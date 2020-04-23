#!/usr/bin/env python
# Copyright (c) 2020 Andrew Carne <andrew_carne@icloud.com>
# This file provides methods for connecting to an SQL database, reading a list of tenure IDs from a
# table, and updating/replacing tenure data in the same or another table.
#
# Currently it is hardcoded to require MS SQL Server.
#
# The input table specification is flexible, but the output table is currently hardcoded:
#   Parcels_Audit
#       Parcel_ID int NOT NULL PRIMARY KEY,
#       Area_ha decimal(8,2) NULL,
#       OwnerRegistration nvarchar(50) NOT NULL,
# 	    RegistrationDate datetime NOT NULL,
# 	    ParcelName nvarchar(20) NOT NULL,
# 	    RegTitleNumber nvarchar(30) NOT NULL,
# 	    NextDueDate datetime NULL,
# 	    JurisdictionMajor_ID int NOT NULL

import sqlalchemy
import urllib
import arcweb_data
import time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Float, func
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class DbDefinition:
    user = ""
    password = ""
    address = ""
    trusted_conn = False
    driver = "{SQL Server Native Client 11.0}"
    database = ""

    def connection_string(self):
        if self.trusted_conn:
            params = urllib.parse.quote_plus("DRIVER=" + self.driver + ";" +
                                             "SERVER=" + self.address + ";" +
                                             "DATABASE=" + self.database + ";" +
                                             "Trusted_Connection=yes")
            return "mssql+pyodbc:///?odbc_connect={}".format(params)
        else:
            params = urllib.parse.quote_plus("DRIVER=" + self.driver + ";" +
                                             "SERVER=" + self.address + ";" +
                                             "DATABASE=" + self.database + ";" +
                                             "UID=" + self.user + ";" +
                                             "PWD=" + self.password)
        return "mssql+pyodbc:///?odbc_connect={}".format(params)


class TableDefinition:
    name = ""
    keyCol = ""
    jurisdictionCol = ""
    required_cols = ["RegDate",
                     "Owner",
                     "Area_ha",
                     "ParcelName",
                     "RegTitleNumber",
                     "NextDueDate"]
    column_map = dict()


def update_tenure(db: DbDefinition, inTable: TableDefinition, outTable: TableDefinition,
                  jurisdiction: str, operation=0):
    """
    Updates tenure in an SQL database
    :param db: input database specification
    :param out_dbdef: output database specification
    :param inTable: input table specification
    :param outTable: output table specification
    :param jurisdiction: jurisdiction code ("NV", "YK", "NWT")
    :param operation: 0 = replace data in outTable; 1 = append data to outTable
    :return:
    """

    db_engine = sqlalchemy.create_engine(db.connection_string())

    conn = db_engine.connect()

    if jurisdiction == "NV":
        data_func = arcweb_data.get_data_NV
        jurisdiction_id = 4
    elif jurisdiction == "YK":
        data_func = arcweb_data.get_data_YK
        jurisdiction_id = 1
    elif jurisdiction == "NWT":
        data_func = arcweb_data.get_data_NWT
        jurisdiction_id = 2
    else:
        raise NotImplementedError

    rows = conn.execute("SELECT " + inTable.keyCol + " FROM " + inTable.name + " WHERE " + inTable.jurisdictionCol +
                           "=" + str(jurisdiction_id))
    tenure_list = [r[inTable.keyCol] for r in rows]

    Session = sessionmaker(bind=db_engine)
    s = Session()

    if operation == 0:
        conn.execute("DELETE FROM " + outTable.name)
        i = 0
    else:
        i = s.query(func.max(AuditParcel.Parcel_ID)).scalar() + 1

    print("Fetching data for " + str(len(tenure_list)) + " tenures...")
    print("[.", end="")
    start = 0
    batch_size = 25
    while start < len(tenure_list):
        end = start + batch_size
        if end > len(tenure_list):
            end = len(tenure_list)

        tenure_data = data_func(tenure_list[start:end])

        for t in tenure_data:
            parcel = AuditParcel()
            parcel.Parcel_ID = i
            parcel.Area_ha = t["Area_ha"]
            parcel.OwnerRegistration = t["Owner"]
            parcel.RegistrationDate = t["RegDate"]
            parcel.RegTitleNumber = t["RegTitleNumber"]
            parcel.NextDueDate = t["NextDueDate"]
            parcel.ParcelName = t["ParcelName"]
            parcel.JurisdictionMajor_ID = jurisdiction_id
            s.add(parcel)
            i = i + 1

        s.commit()
        time.sleep(0.1)
        start = start + batch_size
        print(".", end="")
    print("]\nDone!")


class AuditParcel(Base):
    __tablename__ = "Parcels_Audit"
    Parcel_ID = Column(Integer, primary_key=True, autoincrement=False)
    RegistrationDate = Column(DateTime)
    OwnerRegistration = Column(String)
    Area_ha = Column(Float)
    ParcelName = Column(String)
    RegTitleNumber = Column(String)
    NextDueDate = Column(DateTime)
    JurisdictionMajor_ID = Column(Integer)
