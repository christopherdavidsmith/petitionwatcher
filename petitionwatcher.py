#!/usr/bin/env python

import peewee
import requests
import json
import models
import re
import time
import logging
import logging.config
import datetime


class PetitionWatcher:
    def __init__(self):
        """
        """
        self.logger = logging.getLogger(__name__)
        self.database = peewee.SqliteDatabase('petitions.db')
        models.proxy.initialize(self.database)
        self.database.create_tables([
            models.Country,
            models.Region,
            models.Party,
            models.Constituency,
            models.Petition,
            models.PetitionSnapshot,
            models.PetitionSnapshotByCountry,
            models.PetitionSnapshotByRegion,
            models.PetitionSnapshotByParty,
            models.PetitionSnapshotByConstituency])

        with self.database.atomic():
            self.import_constituencies()
            self.import_petitions()

    def import_constituencies(self):
        """
        """

        # Only continue if there is no party or constituency data in our
        # database
        if models.Party.select() or models.Constituency.select():
            return

        # Construct API URL
        domain = 'http://data.parliament.uk'
        path = '/membersdataplatform/services/mnis/members/query/'
        query = 'House=Commons%7CIsEligible=true'
        url = domain + path + query

        # Fetch constituency data
        response = requests.get(url, headers={'accept': 'application/json'})
        response.encoding = 'utf-8-sig'
        data = json.loads(response.text)

        # Import constituency and party date
        self.logger.info("Importing constituency and party data")
        with self.database.atomic():
            for mp in data['Members']['Member']:
                party = mp['Party']['#text']
                party, created = models.Party.get_or_create(name=party)
                models.Constituency.create(name=mp['MemberFrom'], party=party)
                self.logger.debug(f"Constituency imported: {mp['MemberFrom']}")

    def scan_petitions(self):
        """
        """

        # Scan parliament website and identify number of petitions
        url = 'https://petition.parliament.uk/petitions.json?state=open'
        response = requests.get(url).json()
        last_page = response['links']['last']
        last_page = int(re.search(r'page=(\d+)', last_page).group(1))

        # Iterate 
        petitions = {'import': [], 'update': [], 'update_fake': []}
        self.logger.info("Identifying petitions to import/update")
        last_page = 4
        for page in range(1, last_page + 1):
            self.logger.debug(f"Scraping url: {url}")
            for petition in response['data']:
                signatures = petition['attributes']['signature_count']
                obj = models.Petition.get_or_none(id=petition['id'])

                # If the petition isn't in our database it will need to be
                # imported
                if not obj:
                    petitions['import'].append(petition['id'])
                    continue

                # Else it will need to be updated
                if obj.signatures != signatures:
                    petitions['update'].append(petition['id'])

                else:
                    petitions['update_fake'].append(petition['id'])

            # Fetch the next page
            url = response['links']['next']
            if url:
                response = requests.get(url).json()
                time.sleep(1)

        return petitions


    def import_petitions(self):
        """
        """

        # Obtain list of petitions
        petitions = self.scan_petitions()

        # Import any we don't yet know about
        if petitions['import']:
            self.logger.info(f"Importing {len(petitions['import'])} petitions")
            for petition in petitions['import']:
                self.import_petition(petition)

    def import_petition(self, petition_id):
        """
        """

        # Fetch petition data
        self.logger.debug(f"Importing petition: {petition_id}")
        url = f'https://petition.parliament.uk/petitions/{petition_id}.json'
        response = requests.get(url)
        data = response.json()['data']['attributes']

        # Import initial data
        current_date = datetime.datetime.now()
        petition, created = models.Petition.get_or_create(
            id=petition_id,
            defaults={
                'name': data['action'],
                'date': current_date,
                'signatures': data['signature_count']})

        # Update petition if it already existed
        if not created:
            petition.signatures = data['signature_count']
            petition.date = current_date
            petition.save()

        # Store snapshots
        # Pass the date to the snapshots they are all consistent
        models.PetitionSnapshot.create(
            petition=petition, signatures=data['signature_count'], date=current_date)

        self._snapshot_by_country(petition, data['signatures_by_country'], current_date)
        self._snapshot_by_region(petition, data['signatures_by_region'], current_date)
        self._snapshot_by_constituency(
            petition, data['signatures_by_constituency'], current_date)

    def _snapshot_by_country(self, petition, data, date):
        """
        """

        country_data = []
        for item in data:
            country, _ = models.Country.get_or_create(name=item['name'])
            country_data.append({
                'petition': petition,
                'country': country,
                'date': date,
                'signatures': item['signature_count']})

        models.PetitionSnapshotByCountry.insert_many(country_data).execute()

    def _snapshot_by_region(self, petition, data, date):
        """
        """

        region_data = []
        for item in data:
            region, _ = models.Region.get_or_create(name=item['name'])
            region_data.append({
                'petition': petition,
                'region': region,
                'date': date,
                'signatures': item['signature_count']})

        models.PetitionSnapshotByRegion.insert_many(region_data).execute()

    def _snapshot_by_constituency(self, petition, data, date):
        """
        """

        constituency_data = []
        parties = {}
        for item in data:
            constituency = models.Constituency.get(name=item['name'])
            party = constituency.party
            if party not in parties:
                parties[party] = 0

            parties[party] += item['signature_count']

            constituency_data.append({
                'petition': petition,
                'constituency': constituency,
                'date': date,
                'signatures': item['signature_count']})

        party_data = []
        for party in parties:
            party_data.append({
                'petition': petition,
                'party': party,
                'date': date,
                'signatures': parties[party]})

        models.PetitionSnapshotByConstituency.insert_many(constituency_data).execute()
        models.PetitionSnapshotByParty.insert_many(party_data).execute()


if __name__ == '__main__':

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": True,
        "formatters": {
            "standard": {
                "format": "[%(levelname)s]: %(message)s"
            },
        },
        "handlers": {
            "default": {
                "level": "DEBUG",
                "formatter": "standard",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout"
            }
        },
        "loggers": {
            '__main__': {
                'handlers': ['default'],
                'level': 'DEBUG',
                'propagate': False
            },
        }
    })

    watcher = PetitionWatcher()

