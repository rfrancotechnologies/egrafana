# Grafana exporter

This is an small program that allows you to export Grafana dashboards and datasources and import them to other grafana or just store them as backup.

## Usage

You will require an API token. You can get it on Grafana UI, under `Configuration/API keys`.

With that token, you can list your data:

```
./egrafana.py http://localhost:3000/ list -b <TOKEN>
```

Export your data to the "data" directory:

```
./egrafana.py http://localhost:3000/ export -b <TOKEN>
```

And import it back:

```
./egrafana.py http://localhost:3000/ import -b <TOKEN>
```



## Known issues

- Folders are not generated and Dashboards are moved to main folder.
- Datasources passwords are lost. They must be inserted by hand after importing them or editing the json files.
- Overwriting dashboards or datasources doesn't work yet.
