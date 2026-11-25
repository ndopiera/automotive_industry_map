-- Beschäftigtengrenzen: Destatis GENESIS 52111-0001; EU 2003/361/EG, Anhang Art. 2.
-- https://eur-lex.europa.eu/eli/reco/2003/361/oj?locale=de
-- https://genesis.destatis.de/datenbank/online/table/52111-0001/search/s/NTIxMTEtMDAwMQ%3D%3D
UPDATE company_size SET employees_minimum=0, employees_maximum=9 WHERE size_id=1;
UPDATE company_size SET employees_minimum=10, employees_maximum=49 WHERE size_id=2;
UPDATE company_size SET employees_minimum=50, employees_maximum=249 WHERE size_id=3;
UPDATE company_size SET employees_minimum=250, employees_maximum=NULL WHERE size_id=4;
UPDATE company_size SET employees_minimum=NULL, employees_maximum=NULL WHERE size_id=5;
