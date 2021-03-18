create user wiki_setup_user with PASSWORD 'password';

alter role wiki_setup_user set client_encoding to 'utf8';
alter role wiki_setup_user set default_transaction_isolation to 'read committed';
alter role wiki_setup_user set timezone to 'UTC'; -- TODO use settings
grant all privileges on database wiki to wiki_setup_user; -- TODO use settings
