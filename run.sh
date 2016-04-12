#!/bin/bash

# THIS SCRIPT STARTS TELEMETRY ALERTS PROCEDURES; IT SHOULD BE RUN DAILY

pushd . > /dev/null
cd "$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# perform histogram regression detection
ln /dev/null /dev/raw1394 # this is needed to fix the `libdc1394 error: Failed to initialize libdc1394` error from OpenCV, in alert/alert.py
rm -rf ./histograms Histograms.json &&
wget https://raw.githubusercontent.com/mozilla/gecko-dev/master/toolkit/components/telemetry/Histograms.json -O Histograms.json && # update histogram metadata
nodejs exporter/export.js && # export histogram evolutions using Telemetry.js to JSON, under `histograms/*.JSON`
python alert/alert.py && # perform regression detection and output all found regressions to `dashboard/regressions.json`
python alert/post.py # post all the found regressions above to Medusa, the Telemetry alert system

# various other useful detection/watchdog jobs
python alert/expiring.py email # detect expiring/expired histograms and alert the associated people via email
python alert/crash_aggregates.py email # send out an alert email if the crash aggregates haven't been updated in a while

popd > /dev/null
