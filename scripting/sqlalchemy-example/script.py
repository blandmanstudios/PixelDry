#!/usr/bin/env python3

from sqlalchemy import create_engine, text, Table, MetaData
from sqlalchemy import Column, Integer, String, insert
from sqlalchemy.orm import Session
import yaml

with open('secure_params.yml', 'r') as file:
    params = yaml.safe_load(file)
sqldb_username = params['sqldb_username']
sqldb_password = params['sqldb_password']

engine = create_engine(f"mariadb+pymysql://{sqldb_username}:{sqldb_password}@localhost/wcddb?charset=utf8mb4", future=True)

with engine.connect() as conn:
    result = conn.execute(text("SELECT 'hello world'"))
    print(result.all())

with Session(engine) as session:
    pass

metadata_obj = MetaData()
user_table = Table(
        "user_account",
        metadata_obj,
        Column("id", Integer, primary_key=True),
        Column("name", String(30)),
        Column("fullname", String(30)),
)
metadata_obj.create_all(engine)

smt = insert(user_table).values(name='a', fullname='b')
print(smt)
with engine.connect() as conn:
    result = conn.execute(smt)
    conn.commit()
