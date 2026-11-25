PRAGMA foreign_keys = ON;

CREATE TABLE country (
 country_code TEXT PRIMARY KEY NOT NULL CHECK(country_code GLOB '[A-Z][A-Z]'),
 name_en TEXT NOT NULL, name_de TEXT NOT NULL
);
CREATE TABLE company_size (
 size_id INTEGER PRIMARY KEY, size_code TEXT NOT NULL UNIQUE,
 name_de TEXT NOT NULL, name_en TEXT NOT NULL,
 employees_minimum INTEGER CHECK(employees_minimum >= 0),
 employees_maximum INTEGER CHECK(employees_maximum >= employees_minimum)
);
CREATE TABLE supply_chain_role (
 role_id INTEGER PRIMARY KEY, role_code TEXT NOT NULL UNIQUE,
 name_de TEXT NOT NULL, name_en TEXT NOT NULL
);
CREATE TABLE main_category (
 maincategory_id INTEGER PRIMARY KEY, name_de TEXT NOT NULL UNIQUE, name_en TEXT NOT NULL UNIQUE
);
CREATE TABLE subcategory (
 subcategory_id INTEGER PRIMARY KEY, maincategory_id INTEGER NOT NULL REFERENCES main_category(maincategory_id),
 name_de TEXT NOT NULL, name_en TEXT NOT NULL,
 UNIQUE(maincategory_id,name_de), UNIQUE(maincategory_id,name_en)
);
CREATE TABLE company (
 company_id INTEGER PRIMARY KEY, size_id INTEGER NOT NULL DEFAULT 5 REFERENCES company_size(size_id),
 name TEXT NOT NULL CHECK(length(trim(name)) > 0), website TEXT, description TEXT
);
CREATE TABLE location (
 location_id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES company(company_id),
 country_code TEXT NOT NULL REFERENCES country(country_code),
 state_province_region TEXT, city TEXT NOT NULL, postal_code TEXT,
 address_line_1 TEXT, address_line_2 TEXT,
 latitude REAL CHECK(latitude BETWEEN -90 AND 90),
 longitude REAL CHECK(longitude BETWEEN -180 AND 180),
 CHECK((latitude IS NULL) = (longitude IS NULL)),
 UNIQUE(company_id,location_id)
);
CREATE TABLE source (
 source_id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES company(company_id),
 location_id INTEGER, url TEXT NOT NULL, title TEXT, source_type TEXT,
 accessed_at TEXT, notes TEXT,
 UNIQUE(company_id,source_id),
 FOREIGN KEY(company_id,location_id) REFERENCES location(company_id,location_id)
);
CREATE TABLE company_role (
 company_id INTEGER NOT NULL REFERENCES company(company_id),
 role_id INTEGER NOT NULL REFERENCES supply_chain_role(role_id), source_id INTEGER,
 PRIMARY KEY(company_id,role_id),
 FOREIGN KEY(company_id,source_id) REFERENCES source(company_id,source_id)
);
CREATE TABLE company_category (
 company_id INTEGER NOT NULL REFERENCES company(company_id),
 maincategory_id INTEGER NOT NULL REFERENCES main_category(maincategory_id), source_id INTEGER,
 PRIMARY KEY(company_id,maincategory_id),
 FOREIGN KEY(company_id,source_id) REFERENCES source(company_id,source_id)
);
CREATE TABLE company_subcategory (
 company_id INTEGER NOT NULL REFERENCES company(company_id),
 subcategory_id INTEGER NOT NULL REFERENCES subcategory(subcategory_id), source_id INTEGER,
 PRIMARY KEY(company_id,subcategory_id),
 FOREIGN KEY(company_id,source_id) REFERENCES source(company_id,source_id)
);

INSERT INTO country VALUES ('DE','Germany','Deutschland');
-- Mitarbeitergrenzen: Arbeitsannahme, nicht im Exposé festgelegt.
INSERT INTO company_size VALUES
(1,'MICRO','Kleinstunternehmen','Micro Enterprise',0,9),
(2,'SMALL','Kleines Unternehmen','Small Enterprise',10,49),
(3,'MEDIUM','Mittleres Unternehmen','Medium-sized Enterprise',50,249),
(4,'LARGE','Großunternehmen','Large Enterprise',250,NULL),
(5,'UNKNOWN','Unbekannt','Unknown',NULL,NULL);
INSERT INTO supply_chain_role VALUES
(1,'OEM','OEM','OEM'),
(2,'TIER_1','Tier-1-Zulieferer (Direktzulieferer)','Tier 1 Supplier'),
(3,'TIER_2','Tier-2-Zulieferer','Tier 2 Supplier'),
(4,'TIER_3','Tier-3-Zulieferer','Tier 3 Supplier'),
(5,'INDIRECT','Indirekter Zulieferer','Indirect Supplier'),
(6,'NA','Nicht zutreffend','Not Applicable'),
(7,'UNKNOWN','Unbekannt','Unknown');
INSERT INTO main_category VALUES
(1,'Fahrzeugherstellung','Vehicle Manufacturing'),
(2,'Antriebs- und Energiesysteme','Powertrain & Energy Systems'),
(3,'Fahrwerk, Karosserie und Innenraum','Chassis, Body & Interior'),
(4,'Elektronik, Software und Fahrzeugvernetzung','Electronics, Software & Connectivity'),
(5,'Maschinen-, Anlagenbau und Automatisierung','Machinery & Manufacturing Automation'),
(6,'Mechanische Komponenten, Werkstoffe und Fertigung','Mechanical Components, Materials & Manufacturing'),
(7,'Entwicklung, Prüfung und Validierung','Engineering, Testing & Validation'),
(8,'Motorsport und Performance-Entwicklung','Motorsport & Performance Engineering'),
(9,'Forschung und Innovation','Research & Innovation');
INSERT INTO subcategory (subcategory_id,maincategory_id,name_de,name_en) VALUES
(1,2,'Verbrennungsmotoren','Combustion Engines'),
(2,2,'Elektromotoren','Electric Motors'),
(3,2,'Getriebe','Transmissions'),
(4,2,'Hybridsysteme','Hybrid Systems'),
(5,2,'Brennstoffzellensysteme','Fuel Cell Systems'),
(6,2,'Batteriezellen','Battery Cells'),
(7,2,'Batteriemodule','Battery Modules'),
(8,2,'Batteriesysteme (Batteriepacks)','Battery Packs'),
(9,2,'Batteriemanagementsysteme','Battery Management Systems (BMS)'),
(10,3,'Radaufhängung','Suspension'),
(11,3,'Federn','Springs'),
(12,3,'Stoßdämpfer','Dampers'),
(13,3,'Lenksysteme','Steering Systems'),
(14,3,'Bremssysteme','Braking Systems'),
(15,3,'Räder und Reifen','Wheels & Tires'),
(16,3,'Karosseriestrukturen','Body Structures'),
(17,3,'Leichtbauwerkstoffe','Lightweight Materials'),
(18,3,'Faserverbundbauteile','Composite Components'),
(19,3,'Crashstrukturen','Crash Structures'),
(20,3,'Sitzsysteme','Seating Systems'),
(21,3,'Rückhaltesysteme','Restraint Systems'),
(22,3,'Innenraumkomponenten','Interior Components'),
(23,3,'Mensch-Maschine-Schnittstellen','Human-Machine Interfaces (HMI)'),
(24,4,'Sensoren','Sensors'),
(25,4,'Elektronische Steuergeräte','Electronic Control Units (ECU)'),
(26,4,'Kabelbäume','Wiring Harnesses'),
(27,4,'Leistungselektronik','Power Electronics'),
(28,4,'Beleuchtungssysteme','Lighting Systems'),
(29,4,'Eingebettete Software','Embedded Software'),
(30,4,'Fahrerassistenzsysteme','Advanced Driver Assistance Systems (ADAS)'),
(31,4,'Autonomes Fahren','Autonomous Driving'),
(32,4,'Fahrzeugvernetzung','Vehicle Connectivity'),
(33,4,'Cybersicherheit im Automobilbereich','Automotive Cybersecurity'),
(34,5,'Industrierobotik','Industrial Robotics'),
(35,5,'Werkzeugmaschinen','Machine Tools'),
(36,5,'Produktionslinien','Production Lines'),
(37,5,'SPS- und Steuerungssysteme','PLC & Control Systems'),
(38,5,'Montagesysteme','Assembly Systems'),
(39,6,'Lager und Wälzlager','Bearings'),
(40,6,'Verbindungselemente','Fasteners'),
(41,6,'Dichtungen','Seals'),
(42,6,'Metallbauteile','Metal Components'),
(43,6,'Kunststoffe und Polymere','Plastics & Polymers'),
(44,7,'Fahrzeugarchitektur','Vehicle Architecture'),
(45,7,'Fahrzeugintegration','Vehicle Integration'),
(46,7,'Prototypenbau','Prototyping'),
(47,7,'Prüfstände','Test Benches'),
(48,7,'Simulation','Simulation'),
(49,7,'Komponentenprüfung','Component Testing'),
(50,7,'Fahrzeugprüfung','Vehicle Testing'),
(51,7,'Zertifizierung','Certification');

CREATE INDEX idx_location_company ON location(company_id);
CREATE INDEX idx_location_country_region ON location(country_code,state_province_region);
CREATE INDEX idx_source_company ON source(company_id);
CREATE INDEX idx_subcategory_main ON subcategory(maincategory_id);
PRAGMA foreign_key_check;
