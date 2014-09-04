#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright © 2014 François Bianco <francois.bianco@skadi.ch>

This example can be reuse for any purpose.
"""

import os
from producteev import Producteev

BACKUPS_DIR = 'producteev_backups'

def main():
    # Download every files attached to notes
    p = Producteev()

    try:
        os.mkdir(BACKUPS_DIR)
    except OSError:
        pass

    criteria = {"statuses":[0, 1],} # get active and done tasks
    filters = {'alias':'files', # tasks with files
               'page':1,
               'per_page':50,
               'sort':'created_at',
               'order':'desc'
              }

    # Cycle through all available pages before quitting
    while True:
        
        print "Searching page", filters['page']
        
        tasks_list = p.search_tasks(criteria, filters)
        
        for task in tasks_list['tasks']:
            
            notes_list = p.get_task_notes(task['id'])
            
            for note in notes_list['notes']:
                
                for file_obj in note['files']:

                    print "→ Downloading", file_obj['title']
                    r,c = p.http.request(file_obj['url']) # borrow Producteev http object to download file
                    if '200' == r['status']:
                        with open(os.path.join(BACKUPS_DIR, file_obj['title']),'wb') as f:
                            f.write(c)
                    else:
                        print r, c

        if filters['page']*filters['per_page'] >= tasks_list["total_hits"]:
            break
        filters['page']+=1

if __name__ == '__main__':
  main()