"""Unit tests."""

import unittest
from unittest.mock import Mock, patch, PropertyMock

from charm import MongoDBCharm

from ops.testing import Harness
from oci_image import OCIImageResource, OCIImageResourceError


from ops.model import (
    ActiveStatus,
    BlockedStatus,
    WaitingStatus,
)


class EventDeferal:

    events = []

    def __init__(self, event):
        self.original_event = event

    def fake_event(self, event):
        self.events.append(event)
        return self.original_event(event)

    @property
    def deferred(self):
        if len(self.events) == 1:
            return self.events[0].deferred
        else:
            return False


class TestMongoDB(unittest.TestCase):
    """MongoDB Charm Unit Tests."""

    def setUp(self):
        """Test setup."""
        self.harness = Harness(MongoDBCharm)
        self.harness.set_leader(is_leader=True)
        self.harness.begin()

    # on_install
    @patch("ops.model.Pod.set_spec")
    @patch("charm.MongoDBCharm.on_update_status")
    @patch("oci_image.OCIImageResource.fetch")
    def test_on_install_leader(
        self, mock_image_fetch, mock_on_update_status, mock_set_spec
    ):
        self.harness.charm.on.install.emit()

        # Assertions
        mock_image_fetch.assert_called_once()
        mock_on_update_status.assert_called_once()
        mock_set_spec.assert_called_once()

    @patch("oci_image.OCIImageResource.fetch")
    @patch("charm.MongoDBCharm.on_update_status")
    def test_on_install_non_leader(self, mock_on_update_status, mock_image_fetch):
        self.harness.set_leader(is_leader=False)

        self.harness.charm.on.install.emit()

        # Assertions
        mock_image_fetch.assert_not_called()
        mock_on_update_status.assert_called_once()

    @patch("charm.MongoDBCharm.on_update_status")
    @patch("oci_image.OCIImageResource.fetch")
    def test_on_install_missing_config(self, mock_image_fetch, mock_on_update_status):
        expected_status = BlockedStatus("missing config standalone")

        # Change the config to remove a required parameter
        # Need to disable hooks because we don't want the
        # config_changed hook to be executed.
        self.harness.disable_hooks()
        self.harness.update_config({"standalone": None})
        self.harness.enable_hooks()

        self.harness.charm.on.install.emit()

        # Assertions
        mock_on_update_status.assert_not_called()
        mock_image_fetch.assert_not_called()
        self.assertEqual(self.harness.charm.unit.status, expected_status)

    @patch("ops.model.Pod.set_spec")
    @patch("charm.MongoDBCharm.on_update_status")
    @patch("oci_image.OCIImageResource.fetch")
    def test_on_install_error_fetching_image(
        self, mock_image_fetch, mock_on_update_status, mock_set_spec
    ):
        expected_status = BlockedStatus("Error fetching image information")
        mock_image_fetch.side_effect = OCIImageResourceError("mongodb-image")

        self.harness.charm.on.install.emit()

        # Assertions
        mock_on_update_status.assert_not_called()
        mock_set_spec.assert_not_called()
        mock_image_fetch.assert_called_once()
        self.assertEqual(self.harness.charm.unit.status, expected_status)

    @patch("ops.model.Pod.set_spec")
    @patch("charm.make_pod_spec")
    @patch("charm.MongoDBCharm.on_update_status")
    @patch("oci_image.OCIImageResource.fetch")
    def test_on_install_leader_no_update_pod_spec_state(
        self, mock_image_fetch, mock_on_update_status, mock_make_pod_spec, mock_set_spec
    ):
        pod_spec = {"pod": "spec"}
        mock_make_pod_spec.return_value = pod_spec
        self.harness.charm.state.pod_spec = pod_spec

        self.harness.charm.on.install.emit()

        # Assertions
        mock_image_fetch.assert_called_once()
        mock_on_update_status.assert_called_once()
        mock_set_spec.assert_not_called()

    # on_start
    @patch("charm.MongoDBCharm.on_mongodb_started")
    @patch("mongo.MongoConnector.ready")
    @patch("charm.MongoDBCharm.on_update_status")
    def test_on_start_leader_ready(
        self, mock_on_update_status, mock_mongo_ready, mock_on_mongodb_started
    ):
        mock_mongo_ready.return_value = True
        self.harness.charm.on.start.emit()

        # Assertions
        # mock_on_update_status.assert_called_once()
        mock_on_mongodb_started.assert_called_once()

    @patch("mongo.MongoConnector.ready")
    @patch("charm.MongoDBCharm.on_update_status")
    def test_on_start_leader_not_ready(self, mock_on_update_status, mock_mongo_ready):
        mock_mongo_ready.return_value = False
        event_deferal = EventDeferal(self.harness.charm.on_start)
        self.harness.charm.on_start = event_deferal.fake_event

        self.harness.charm.on.start.emit()

        # Assertions
        # mock_on_update_status.assert_called_once()
        self.assertTrue(event_deferal.deferred)

    @patch("mongo.MongoConnector.ready")
    @patch("charm.MongoDBCharm.on_update_status")
    def test_on_start_non_leader(self, mock_on_update_status, mock_mongo_ready):
        self.harness.set_leader(is_leader=False)
        self.harness.charm.on.start.emit()
        mock_on_update_status.assert_not_called()
        mock_mongo_ready.assert_not_called()


class TestCharmStandalone(TestMongoDB):
    """MongoDB Charm Unit Tests. (standalone)"""

    def setUp(self):
        """Test setup."""
        self.harness = Harness(MongoDBCharm)
        self.harness.set_leader(is_leader=True)
        self.harness.update_config({"standalone": True})
        self.harness.begin()
        self.assertTrue(self.harness.charm.model.config["standalone"])

    # on_start
    @patch("cluster.MongoDBCluster.on_cluster_ready")
    @patch("mongo.MongoConnector.ready")
    @patch("charm.MongoDBCharm.on_update_status")
    def test_on_start_leader_ready(
        self, mock_on_update_status, mock_mongo_ready, mock_on_cluster_ready
    ):
        mock_mongo_ready.return_value = True
        self.harness.charm.on.start.emit()
        # Assertions
        # mock_on_update_status.assert_called_once()
        mock_on_cluster_ready.assert_not_called()

    # on_update_status
    @patch("mongo.MongoConnector.ready")
    def test_on_update_status_standalone_ready(self, mock_mongo_ready):
        mock_mongo_ready.return_value = True
        excepted_status = ActiveStatus("standalone-mode: ready")
        self.harness.charm.on.update_status.emit()
        self.assertEqual(self.harness.charm.unit.status, excepted_status)

    @patch("mongo.MongoConnector.ready")
    def test_on_update_status_standalone_not_ready(self, mock_mongo_ready):
        mock_mongo_ready.return_value = False
        excepted_status = WaitingStatus("standalone-mode: service not ready yet")
        self.harness.charm.on.update_status.emit()
        self.assertEqual(self.harness.charm.unit.status, excepted_status)


class TestCharmReplicaSet(TestMongoDB):
    """Mongodb Charm Unit Tests (replica set mode)."""
    def setUp(self):
        """Test setup."""
        self.harness = Harness(MongoDBCharm)
        self.harness.set_leader(is_leader=True)
        self.replica_set_name = "myreplica"
        self.harness.update_config(
            {"standalone": False, "replica_set_name": self.replica_set_name}
        )
        self.harness.begin()
        self.assertFalse(self.harness.charm.model.config["standalone"])

    # on_start
    @patch("mongo.MongoConnector.replset_initialize")
    @patch("cluster.MongoDBCluster.on_cluster_ready")
    @patch("mongo.MongoConnector.ready")
    @patch("charm.MongoDBCharm.on_update_status")
    def test_on_start_leader_ready(
        self,
        mock_on_update_status,
        mock_mongo_ready,
        mock_on_cluster_ready,
        mock_replset_initialize,
    ):
        mock_mongo_ready.return_value = True

        self.harness.charm.on.start.emit()

        # Assertions
        # mock_on_update_status.assert_called_once()
        mock_on_cluster_ready.assert_called_once()
        mock_replset_initialize.assert_called_once()

    @patch("mongo.MongoConnector.replset_initialize")
    @patch("cluster.MongoDBCluster.on_cluster_ready")
    @patch("cluster.MongoDBCluster.replica_set_initialized")
    @patch("mongo.MongoConnector.ready")
    @patch("charm.MongoDBCharm.on_update_status")
    def test_on_start_leader_replset_initialized(
        self,
        mock_on_update_status,
        mock_mongo_ready,
        mock_replica_set_initialized,
        mock_on_cluster_ready,
        mock_replset_initialize,
    ):
        mock_replica_set_initialized.return_value = True
        mock_mongo_ready.return_value = True

        self.harness.charm.on.start.emit()

        # Assertions
        # mock_on_update_status.assert_called_once()
        mock_on_cluster_ready.assert_called_once()
        mock_replset_initialize.assert_not_called()

    # on_update_status
    @patch("cluster.MongoDBCluster.replica_set_hosts", new_callable=PropertyMock)
    @patch("cluster.MongoDBCluster.ready")
    @patch("mongo.MongoConnector.ready")
    def test_on_update_status_replset_ready(
        self, mock_mongo_ready, mock_cluster_ready, mock_replica_set_hosts
    ):
        mock_replica_set_hosts.return_value = ["one_member"]
        mock_mongo_ready.return_value = True
        mock_cluster_ready.return_value = True
        excepted_status = ActiveStatus(f"replica-set-mode({self.replica_set_name}): ready (1 members)")
        self.harness.charm.on.update_status.emit()
        self.assertEqual(self.harness.charm.unit.status, excepted_status)

    @patch("mongo.MongoConnector.ready")
    def test_on_update_status_replset_ready_non_leader(
        self, mock_mongo_ready
    ):
        self.harness.set_leader(is_leader=False)
        mock_mongo_ready.return_value = True
        excepted_status = ActiveStatus(f"replica-set-mode({self.replica_set_name}): ready")
        self.harness.charm.on.update_status.emit()
        self.assertEqual(self.harness.charm.unit.status, excepted_status)

    @patch("cluster.MongoDBCluster.ready", new_callable=PropertyMock)
    @patch("mongo.MongoConnector.ready")
    def test_on_update_status_replset_replica_not_ready(
        self, mock_mongo_ready, mock_cluster_ready
    ):
        mock_mongo_ready.return_value = True
        mock_cluster_ready.return_value = False
        excepted_status = WaitingStatus(
            f"replica-set-mode({self.replica_set_name}): ready (replica set not initialized yet)"
        )
        self.harness.charm.on.update_status.emit()
        self.assertEqual(self.harness.charm.unit.status, excepted_status)

    @patch("mongo.MongoConnector.ready")
    def test_on_update_status_replset_service_not_ready(self, mock_mongo_ready):
        mock_mongo_ready.return_value = False
        excepted_status = WaitingStatus(
            f"replica-set-mode({self.replica_set_name}): service not ready yet"
        )
        self.harness.charm.on.update_status.emit()
        self.assertEqual(self.harness.charm.unit.status, excepted_status)



if __name__ == "__main__":
    unittest.main()
