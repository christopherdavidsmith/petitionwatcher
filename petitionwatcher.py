#!/usr/bin/env python

import peewee
import requests
import json
import models
import re
import time


class PetitionWatcher:
    def __init__(self):
        """
        """
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

        self.import_constituencies()
        self.import_petitions()

    def import_constituencies(self):
        """
        """

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
        with self.database.atomic():
            for mp in data['Members']['Member']:
                party = mp['Party']['#text']
                party, created = models.Party.get_or_create(name=party)
                models.Constituency.create(name=mp['MemberFrom'], party=party)

    def import_petitions(self):
        """
        """
        petitions = self.scan_petitions()

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
        for page in range(1, last_page + 1):
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

if __name__ == '__main__':
    watcher = PetitionWatcher()
