#!/usr/bin/env python3
import unittest
from wcdraw.common import timestring_to_datetime

class TestMethods(unittest.TestCase):
    def test_characters_to_mysql(self):
        special_string = 'ﺖﻳ  and 设 and sław  and ך'

        pass
    def test_strings_to_timestamps(self):
        typical_time = '2023-12-30T02:04:29.52+00:00'
        atypical_time = '2023-12-30T02:04:29+00:00'
        timestamp = timestring_to_datetime(typical_time)
        timestamp = timestring_to_datetime(atypical_time)
        pass



if __name__ == '__main__':
    unittest.main()
