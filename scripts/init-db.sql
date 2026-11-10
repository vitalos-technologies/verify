-- Local/CI bootstrap: migration owner role and databases. Runtime roles are created by migrations.
CREATE ROLE vv_owner LOGIN PASSWORD 'vv_owner_local' CREATEROLE CREATEDB;
CREATE DATABASE vv_dev OWNER vv_owner;
CREATE DATABASE vv_test OWNER vv_owner;
CREATE DATABASE vv_e2e OWNER vv_owner;
