#!/usr/bin/env python
import os
import json
import argparse
import logging
import requests

logger = logging.getLogger(__name__)


def configure_logging(verbosity):
    msg_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    VERBOSITIES = [logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG]
    level = VERBOSITIES[min(int(verbosity), len(VERBOSITIES) - 1)]
    formatter = logging.Formatter(msg_format)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)


def parse_args():
    parser = argparse.ArgumentParser(description="Importer/Exporter for Grafana data")
    parser.add_argument(
        "server", help="Server url"
    )
    parser.add_argument(
        "action", nargs='?', choices=('list', 'export', 'import'), default='list', help="Action to be performed"
    )
    parser.add_argument(
        "-b", "--bearer", help="Bearer header"
    )
    parser.add_argument(
        "-p", "--path", default="data", help="Path to import/export"
    )
    parser.add_argument(
        "--override", default=False, action="store_true", help="Override if already exists (only for import)"
    )
    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="Increase verbosity"
    )
    return parser.parse_args()


class Grafana:
    def __init__(self, url, bearer):
        self.url = url
        self.bearer = bearer
        self.session = requests.Session()

    def _get(self, path):
        headers = {}
        if self.bearer:
            headers["Authorization"] = f"Bearer {self.bearer}"
        r = self.session.get(f"{self.url}{path}", headers=headers)
        r.raise_for_status()
        return r

    def _post(self, path, content, override):
        headers = {
            'Content-Type': 'application/json',
            'Accept': "application/json",
        }
        if self.bearer:
            headers["Authorization"] = f"Bearer {self.bearer}"
        r = self.session.post(f"{self.url}{path}", headers=headers, json=content)
        if override and r.status_code == override:
            #logger.debug("Already exists, but will be overriden")
            #r = self._put(path, content)
            logger.warning("Overriding is not implemented yet")
            return
        print(r.content)
        r.raise_for_status()
        return r

    def _put(self, path, content):
        headers = {
            'Content-Type': 'application/json',
            'Accept': "application/json",
        }
        if self.bearer:
            headers["Authorization"] = f"Bearer {self.bearer}"
        r = self.session.post(f"{self.url}{path}", headers=headers, json=content)
        print(r.content)
        r.raise_for_status()
        return r

    def _dashboard_list(self):
        r = self._get("/api/search?query=&")
        return r.json()

    def _datasources_list(self):
        r = self._get("/api/datasources")
        return r.json()

    def _alert_list(self):
        r = self._get("/api/alert-notifications")
        return r.json()

    def list(self):
        for item in self._dashboard_list():
            print(f"dashboard: {item['type']} - {item['title']}")        
        for item in self._datasources_list():
            print(f"datasource: {item['type']} - {item['name']}")        
        for item in self._alert_list():
            print(f"alert: {item['type']} - {item['name']}")        
             
    def _create_directories(self, base):
        for d in ("dashboards", "datasources"):
            directory = os.path.join(base, d)
            if (os.path.exists(directory)):
                logger.info(f"Reusing directory {directory}")
            else:
                os.makedirs(directory)
                logger.info(f"Created directory {directory}")

    def _save(self, filename, data):
        logger.debug(f"Saving {filename}")
        with open(filename, 'w+') as fd:
            json.dump(data, fd, indent=2)

    def export(self, directory):
        self._create_directories(directory)
        for item in self._dashboard_list():
            data = self._get(f"/api/dashboards/{item['uri']}")
            filename = os.path.join(directory, "dashboards", f"{item['uri'].replace('/', '_')}.json")
            self._save(filename, data.json())
        for item in self._datasources_list():
            filename = os.path.join(directory, "datasources", f"{item['name'].replace('/', '_')}.json")
            data = dict(
                meta=dict(
                    type="datasource"
                ),
                datasource=item
            )
            self._save(filename, data)

    def insert_file(self, path, override):
        logger.info(f"Processing file {path}")
        with open(path) as fd:
            data = json.load(fd)
        try:
            meta = data['meta']
            logger.info(f'file {path} has a type {meta["type"]}')
            if meta['type'] == 'datasource':
                return
                self._post('/api/datasources', data['datasource'], 409 if override else None)
            elif meta['type'] == 'db':
                data['dashboard']['id'] = None
                data['dashboard']['uid'] = None
                del data['meta']
                self._post('/api/dashboards/db', data, 412 if override else None)
            else:
                raise Exception(f"Unsupported type: {meta['type']}")
        except Exception as e:
            logger.error(f'file {path} could not be imported: {e}')            

    def insert(self, directory, override):
        for root, dirs, files in os.walk(directory):
            for f in files:
                if not f.endswith('.json'):
                    continue
                fullpath = os.path.join(root, f)
                self.insert_file(fullpath, override)

def main():
    args = parse_args()
    configure_logging(args.verbose)
    grafana = Grafana(args.server, args.bearer)

    actions = {
        'list': {'f': grafana.list},
        'export': {'f': grafana.export, 'kwargs': {'directory': args.path}},
        'import': {'f': grafana.insert, 'kwargs': {'directory': args.path, 'override': args.override}},
    }

    action = actions[args.action]
    logger.debug(f"Running action {args.action}")
    action['f'](**action.get('kwargs', {}))

if __name__ == "__main__":
    main()
