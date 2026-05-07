import logging
import os
from google.cloud.devtools import cloudbuild
from google.cloud.devtools.cloudbuild import Build
from typing import Dict

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())

class BuildSummary:
    latest_non_failure_status: Build.Status = None
    retriable: bool = False
    latest_try_count: int = 0
    latest_attempt_failed: bool = False

    def flag_first_non_failure_build(self, build: cloudbuild.Build):
        # NOTE on processing order and retry logic:
        # 1. Processing Order: Since ListBuilds returns newest first, this loop processes builds from newest to oldest.
        # 2. Logic Intent: This logic effectively finds the most recent non-failure build (moving backwards in time)
        #    and uses its status to determine if we should retry.
        # 3. Retry Condition: It will only allow a retry if the newest build failed AND the cluster has not succeeded
        #    in any of the previous recorded attempts in this history window.
        # 4. Usage Context: Note that this `retriable` result is only checked in main.py when cluster_exists is True
        #    or when there are not enough free machines.

        # latest_non_failure_status will only be updated with non-failure statuses.
        if build.status in (cloudbuild.Build.Status.QUEUED, cloudbuild.Build.Status.PENDING, cloudbuild.Build.Status.WORKING, cloudbuild.Build.Status.SUCCESS):
            self.latest_non_failure_status = build.status
            self.retriable = False
        else:
            # Any status in this category can be treated as a failure
            self.retriable = True

class BuildHistory:
    def __init__(self, project_id: str, region: str, max_retries: int, trigger_name: str):
        self.project_id = project_id
        self.region = region
        self.max_retries = max_retries
        self.trigger_name = trigger_name
        self.client = cloudbuild.CloudBuildClient()
        self.builds: Dict[tuple[str, str], BuildSummary] = self._get_build_history()

    def _get_build_history(self) ->Dict[tuple[str, str], BuildSummary]:
        """
        Queries for Cloud Build history matching a specific trigger name.

        Args:
            trigger_name: The name of the Cloud Build trigger.

        Returns:
            A dictionary with the zone name and intent hash tuple as the key 
            and the build summary which contains relevant information to 
            determine if a retry should be triggered.
        """
        trigger_request = cloudbuild.ListBuildTriggersRequest(
            project_id = self.project_id,
            parent = f"projects/{self.project_id}/locations/{self.region}"
        )

        trigger_name_filter = ""

        triggers = self.client.list_build_triggers(trigger_request)

        for trigger in triggers:
            if (trigger.name == self.trigger_name):
                if trigger_name_filter == "":
                    trigger_name_filter += f"trigger_id={trigger.id}"
                else:
                    trigger_name_filter += f" OR trigger_id={trigger.id}"

        if trigger_name_filter == "":
            raise Exception(f"No triggers found named {self.trigger_name}")

        request = cloudbuild.ListBuildsRequest(
            project_id=self.project_id,
            filter=trigger_name_filter,
            parent = f"projects/{self.project_id}/locations/{self.region}"
        )

        page_result = self.client.list_builds(request=request)

        # Only page through last 1,000 builds
        build_entries = 0
        build_summary_dict: Dict[tuple[str, str], BuildSummary] = dict()

        for response in page_result:
            build_entries += 1

            if build_entries > 1000:
                break

            zone = ""
            intent_hash = ""

            for key in response.substitutions:
                if key == "_ZONE":
                    zone = response.substitutions[key]
                elif key == "_INTENT_HASH":
                    intent_hash = response.substitutions[key]

            if not zone:
                # Builds are expected to have the _ZONE substitution. This is the value that is
                # matched on to calculate whether a build should be retried or not. 
                logger.warning(f"build found without _ZONE substitution, skipping... Build ID: {response.id}")
                continue

            key = (zone, intent_hash)

            if key in build_summary_dict:
                summary = build_summary_dict[key]
                # Since we process from newest to oldest, once we have found a non-failure
                # status (latest_non_failure_status is set), older builds will not change the outcome.
                # We can safely skip calling flag_first_non_failure_build for them.
                if summary.latest_non_failure_status is not None:
                    continue
                summary.flag_first_non_failure_build(response)
            else:
                summary = BuildSummary()
                
                # Check if the absolute newest build failed
                summary.latest_attempt_failed = response.status not in (
                    cloudbuild.Build.Status.SUCCESS,
                    cloudbuild.Build.Status.WORKING,
                    cloudbuild.Build.Status.QUEUED,
                    cloudbuild.Build.Status.PENDING
                )
                
                try_count_str = response.substitutions.get("_TRY_COUNT", "0")
                summary.latest_try_count = int(try_count_str)
                summary.flag_first_non_failure_build(response)
                logger.info(f"Found latest build for zone {zone} with hash {intent_hash}. Latest try_count={summary.latest_try_count}, latest_attempt_failed={summary.latest_attempt_failed}")
                build_summary_dict[key] = summary

        return build_summary_dict

    def should_retry_zone_build(self, zone_name: str, intent_hash: str):
        """
        Determines if a build should be retried or not. `False` is returned in the event 
        of no build history for a zone. 

        Args:
            zone_name: The name of the zone
            intent_hash: The hash of the cluster intent
        """
        if not zone_name:
            raise Exception('missing zone_name')
        
        key = (zone_name, intent_hash)
        if key not in self.builds:
            return False
        else:
            build = self.builds[key]
            return build.retriable

    def get_latest_try_count(self, zone_name: str, intent_hash: str) -> int:
        """
        Returns the latest try count for a zone and intent hash.
        """
        key = (zone_name, intent_hash)
        if key not in self.builds:
            return 0
        return self.builds[key].latest_try_count

        
        