#!/usr/bin/env python

"Setuptools params"

from setuptools import setup
from os.path import join

# Get version number from source tree
import sys
sys.path.append( '.' )
from mininet-original.net import VERSION

scripts = [ join( 'bin', filename ) for filename in [ 'mn' ] ]

modname = distname = 'mininet-wifi'

setup(
    name=distname,
    version=VERSION,
    description='Process-based OpenFlow emulator',
    author='Bob Lantz; Ramon Fontes',
    author_email='rlantz@cs.stanford.edu; ramonrf@dca.fee.unicamp.br',
    packages=[ 'mininet-original', 'mininet-wifi.wifi', 'mininet-wifi.sixLoWPAN', 'mininet-wifi.data', 'mininet-wifi.examples', 'mininet-wifi.sumo', 'mininet-wifi.sumo.sumolib',
               'mininet-wifi.sumo.traci', 'mininet-wifi.sumo.data', 'mininet-wifi.sumo.sumolib.net', 'mininet-wifi.sumo.sumolib.output',
               'mininet-wifi.sumo.sumolib.shapes', 'mininet-wifi.utils' ],
    package_data={'mininet-wifi.sumo.data': ['*.xml', '*.sumocfg'], 'mininet-wifi.data': ['signal_table_ieee80211ax']},
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
