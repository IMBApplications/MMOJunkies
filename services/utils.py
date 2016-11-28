#!/usr/bin/env python
# -*- coding: utf-8 -*-

import yaml


class YamlConfig(object):
    def __init__(self, filename=None):
        self.filename = filename
        self.values = {}
        if filename:
            self.load()

    def load(self):
        f = open(self.filename)
        self.values = yaml.safe_load(f)
        f.close()

    def get_values(self):
        return self.values

    def set_values(self, values):
        self.values = values
