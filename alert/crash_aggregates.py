#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys
import re
from datetime import datetime, date, timedelta

import boto

from mail import send_ses
from mozilla_versions import version_compare, version_get_major, version_normalize_nightly

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

S3_BUCKET = "telemetry-test-bucket"
S3_PREFIX = "crash_aggregates/v1/" # must end with a slash

FROM_ADDR                 = "telemetry-alerts@mozilla.com" # email address to send alerts from
GENERAL_TELEMETRY_ALERT   = "dev-telemetry-alerts@lists.mozilla.org" # email address that will receive all notifications, 6 weeks beforeexpiry

def print_help():
    print "Check if the crash rate aggregator job is giving the expected output."
    print "Usage: {} email|test".format(sys.argv[0])
    print "  {} email [YYYY-MM-DD]   if crash aggregates haven't been updated in about a day as of YYYY-MM-DD (defaults to current date), email the telemetry alerts mailing list saying so".format(sys.argv[0])
    print "  {} test  [YYYY-MM-DD]   print out whether crash aggregates have been updated in about a day as of YYYY-MM-DD (defaults to current date)".format(sys.argv[0])

def is_job_failing(current_date):
    # obtain the S3 bucket
    conn = boto.connect_s3()
    try:
        bucket = conn.get_bucket(S3_BUCKET, validate=False)
    except boto.exception.S3ResponseError: # bucket doesn't exist
        return True

    # list all of the prefixes under the given one
    crash_aggregate_partitions = bucket.list(prefix=S3_PREFIX, delimiter="/")
    start, end = current_date - timedelta(days=2), current_date
    for partition in crash_aggregate_partitions:
        match = re.search(r"/submission_date=(\d\d\d\d-\d\d-\d\d)/$", partition.name)
        if not match: continue
        submission_date = datetime.strptime(match.group(1), "%Y-%m-%d").date()
        if start <= submission_date <= end:
            return False # found suitable partition, job is working

    # no suitable partition found, job is failing
    return True

if __name__ == "__main__":
    # process command line arguments
    if not (2 <= len(sys.argv) <= 3) or sys.argv[1] not in {"email", "test"}:
        print_help()
        sys.exit(1)
    is_dry_run = sys.argv[1] == "test"
    now = date.today()
    if len(sys.argv) >= 3:
        try: now = datetime.strptime(sys.argv[2], "%Y-%m-%d").date()
        except ValueError:
            print "Unknown/invalid date: {}".format(sys.argv[2])
            print_help()
            sys.exit(1)
    else:
        now = date.today()

    if is_dry_run:
        if is_job_failing(now):
            print("Crash aggregates have not been updated for 2 days as of {}.".format(now))
        else:
            print("Crash aggregates have been updated within 2 days before {}.".format(now))
    elif is_job_failing(now):
        print("Sending email notification about crash aggregates not being updated to {}.".format(GENERAL_TELEMETRY_ALERT))
        email_body = (
            "As of {}, the daily crash aggregates job [1] has not output results for 2 days. This is an automated message from Cerberus [2].\n"
            "\n"
            "[1]: https://github.com/mozilla/moz-crash-rate-aggregates\n"
            "[2]: https://github.com/mozilla/cerberus\n"
        ).format(now)
        send_ses(FROM_ADDR, "[FAILURE] Crash aggregates not updating", email_body, GENERAL_TELEMETRY_ALERT)
