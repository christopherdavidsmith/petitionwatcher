#!/usr/bin/env python

import peewee
import models


class PetitionWatcher:
    def __init__(self):
        """
        """
        with peewee.SqliteDatabase('petitions.db') as database:
            models.proxy.initialize(database)
            database.create_tables([
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

if __name__ == '__main__':
    watcher = PetitionWatcher()
