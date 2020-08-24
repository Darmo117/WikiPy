# TODO use settings for DB name
psql postgres -c "CREATE DATABASE wiki WITH ENCODING 'UTF8'"
psql wiki -f setup.sql
