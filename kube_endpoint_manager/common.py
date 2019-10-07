# -*- coding: utf-8 -*-

# Copyright (c) 2019 Martin Dojcak
# See LICENSE for details.

'''External kubernetes endpoint manager module common
'''

class MetaSingleton(type):
    """Singleton metaclass
    """
    __singleton_instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls.__singleton_instances:
            cls.__singleton_instances[cls] = super().__call__(*args, **kwargs)

        return cls.__singleton_instances[cls]
