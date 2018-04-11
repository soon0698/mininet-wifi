#!/usr/bin/env python

"Setuptools params"

from setuptools import setup
from os.path import join

# Get version number from source tree
import sys
sys.path.append( '.' )
from mininet_original.net import VERSION

scripts = [ join( 'bin', filename ) for filename in [ 'mn' ] ]

modname = distname = 'mininet-wifi'

setup(
    name=distname,
    version=VERSION,
    description='Process-based OpenFlow emulator',
    author='Bob Lantz; Ramon Fontes',
    author_email='rlantz@cs.stanford.edu; ramonrf@dca.fee.unicamp.br',
    packages=[ 'mininet_original', 'mininet_wifi.wifi', 'mininet_wifi.sixLoWPAN', 'mininet_wifi.data', 'mininet_wifi.examples', 'mininet_wifi.sumo', 'mininet_wifi.sumo.sumolib',
               'mininet_wifi.sumo.traci', 'mininet_wifi.sumo.data', 'mininet_wifi.sumo.sumolib.net', 'mininet_wifi.sumo.sumolib.output',
               'mininet_wifi.sumo.sumolib.shapes', 'mininet_wifi.utils' ],
    package_data={'mininet_wifi.sumo.data': ['*.xml', '*.sumocfg'], 'mininet_wifi.data': ['signal_table_ieee80211ax']},
    long_description="""
        Mininet-WiFi is a network emulator which uses lightweight
        virtualization to create virtual networks for rapid
        prototyping of Software-Defined Wireless Network (SDWN) designs
        using OpenFlow.
        """,
    classifiers=[
          "License :: OSI Approved :: BSD License",
          "Programming Language :: Python",
          "Development Status :: 5 - Production/Stable",
          "Intended Audience :: Developers",
          "Topic :: System :: Emulators",
    ],
    keywords='networking emulator protocol Internet OpenFlow SDN',
    license='BSD',
    install_requires=[
        'setuptools'
    ],
    scripts=scripts,
)
