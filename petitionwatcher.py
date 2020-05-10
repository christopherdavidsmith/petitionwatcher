#!/usr/bin/env python

import peewee
import requests
import json
import models


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

if __name__ == '__main__':
    watcher = PetitionWatcher()
