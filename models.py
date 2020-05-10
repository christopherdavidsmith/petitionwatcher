from datetime import datetime
import peewee

proxy = peewee.Proxy()

class BaseModel(peewee.Model):
    class Meta:
        database = proxy

class AbstractItemWithDate(BaseModel):
    date = peewee.DateTimeField(default=datetime.now)

    def seconds_since_date(self):
        """
        Return the number of seconds which have elapsed since the
        date stored in the date field of the current item
        """
        current_date = datetime.now()
        current_time = datetime.timestamp(current_date)
        previous_time = datetime.timestamp(self.date)

        return current_time - previous_time

    def minutes_since_date(self):
        """
        Return then number of minutes which have alapsed since the
        date stored in the fate field of the current item
        """
        return self.seconds_since_date() / 60

class AbstractItemWithSignatures(AbstractItemWithDate):
    signatures = peewee.IntegerField(default=0)

    def signatures_per_minute(self):
        """
        Given a number of signatures, what is the rate at which
        signatures are increasing per minute
        """
        sig_difference = signatures - self.signatures
        try:
            return int(sig_difference / self.minutes_since_date())
        except ZeroDivisionError:
            return 0

class Country(BaseModel):
    name = peewee.CharField()

class Region(BaseModel):
    name = peewee.CharField()

class Party(BaseModel):
    name = peewee.CharField()

class Constituency(BaseModel):
    name = peewee.CharField()
    party = peewee.ForeignKeyField(Party, backref='constituencies')

class Petition(AbstractItemWithSignatures):
    id = peewee.IntegerField(primary_key=True)
    name = peewee.CharField()

class PetitionSnapshot(AbstractItemWithSignatures):
    petition = peewee.ForeignKeyField(Petition, backref='snapshots')

class PetitionSnapshotByCountry(PetitionSnapshot):
    country = peewee.ForeignKeyField(Country, backref='snapshots')

class PetitionSnapshotByRegion(PetitionSnapshot):
    region = peewee.ForeignKeyField(Region, backref='snapshots')

class PetitionSnapshotByParty(PetitionSnapshot):
    party = peewee.ForeignKeyField(Party, backref='snapshots')

class PetitionSnapshotByConstituency(PetitionSnapshot):
    constituency = peewee.ForeignKeyField(
        Constituency, 
        backref='snapshots')
