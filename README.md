# Unternehmenskarte Automobilbranche

1. Vorhandene lokale Datenbank sichern.
2. Inhalt des Strukturpakets in das geklonte Repo kopieren. Bestehende Dateien zuvor außerhalb des Repos sichern.
3. Aktuelle Arbeitsdatenbank als `01_Database/companies_automotive_industry_work.db` kopieren (nicht committen).
4. `02_Data_Management/Start_Windows.bat` starten; V3-Migration durchführen lassen.
5. In Veröffentlichung bei Bedarf Testfreigaben einschließen, Snapshot herunterladen und als `01_Database/companies_automotive_industry.db` speichern.
6. Vorhandene Website aus dem bisherigen Repo nach `04_Web_Map/index.html` kopieren, sofern vorhanden; die enthaltene Datei ist nur ein Platzhalter.
7. Alte Exportdatei und alte öffentliche DB im Hauptverzeichnis entfernen, ggf. alten public-Ordner entfernen (vorher sichern). Nur einen deploy-Workflow behalten.
8. In GitHub Desktop Änderungen kontrollieren, committen und pushen. Niemals Arbeits-DB, Backups oder Token hochladen.

GeoJSON: https://ndopiera.github.io/unternehmenskarte_automobilbranche/unternehmen.geojson

Siehe 05_Documentation/ANLEITUNG.md.

Markergenerierung: `03_Data_Export/markers/` (Farben, Piktogramme, Renderer).
