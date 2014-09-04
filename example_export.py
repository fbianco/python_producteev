#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright © 2014 François Bianco <francois.bianco@skadi.ch>

This example can be reuse for any purpose.
"""

import gzip
from producteev import Producteev

def main():
    # Dump task in CSV
    p = Producteev()


    criteria={"statuses":[0, 1],} # get active and done tasks
    file_url = p.export_tasks(criteria)['file']['url']
    print "→ Downoald exported file", file_url
    r,c = p.http.request(file_url) # borrow Producteev http

    if r['status'] == '200':
        with gzip.open('producteev_exported.csv.gz','wb') as f:
            f.write(c)
        print 'Saved to producteev_exported.csv.gz'
    else:
        print 'Failled'
        print r, c

if __name__ == '__main__':
  main()