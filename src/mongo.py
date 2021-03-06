from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
import logging

logger = logging.getLogger(__name__)


class MongoConnector:
    @staticmethod
    def ready(uri):
        ready = False
        client = MongoClient(uri, serverSelectionTimeoutMS=1000)
        try:
            client.server_info()
            ready = True
            logger.debug("mongodb service is ready.")
        except ServerSelectionTimeoutError:
            logger.debug("mongodb service is not ready yet.")
        finally:
            client.close()
        return ready

    @staticmethod
    def replset_generate_config(
        hosts: list,
        replica_set_name: str,
        increase_version: bool = False,
        config: dict = {},
    ):
        new_config = config.copy()
        new_config["_id"] = replica_set_name
        new_config["members"] = [{"_id": i, "host": h} for i, h in enumerate(hosts)]
        if "version" in new_config and increase_version:
            new_config["version"] += 1
        return new_config

    @staticmethod
    def replset_initialize(uri: str, config: dict):
        client = MongoClient(uri, serverSelectionTimeoutMS=1000)
        try:
            logger.debug(f"initializing replica set with config={config}")
            client.admin.command("replSetInitiate", config)
        except Exception as e:
            logger.error(f"cannot initialize replica set. error={e}")
        finally:
            client.close()

    @staticmethod
    def replset_reconfigure(uri: str, config: dict):
        replset_client = MongoClient(uri, serverSelectionTimeoutMS=1000)
        try:
            replset_client.admin.command("replSetReconfig", config, force=True)
        except Exception as e:
            logger.error(f"cannot reconfigure replica set. error={e}")
        finally:
            replset_client.close()

    @staticmethod
    def replset_get_config(uri: str):
        replset_client = MongoClient(uri, serverSelectionTimeoutMS=1000)
        config = None
        try:
            config = replset_client.admin.command("replSetGetConfig")["config"]
        except Exception as e:
            logger.error(f"cannot get replica set config. error={e}")
        finally:
            replset_client.close()
        return config


# class Mongo:
#     def __init__(self, standalone_uri, replica_set_uri=None):
#         self.standalone_uri = standalone_uri
#         self.replica_set_uri = replica_set_uri
#         self.replica_set_name = None
#         if "?" in replica_set_uri:
#             (_, opts) = replica_set_uri.split("?")
#             opts = opts.split("&") if "&" in opts else [opts]
#             options = {
#                 self.key_from_opt(opt): self.value_from_opt(opt)
#                 for opt in opts
#                 if "=" in opt
#             }
#             self.replica_set_name = options.get("replicaSet")

#     def key_from_opt(self, opt):
#         return opt.split("=")[0]

#     def value_from_opt(self, opt):
#         return opt.split("=")[1]

#     def get_client(self):
#         return MongoClient(self.standalone_uri, serverSelectionTimeoutMS=1000)

#     def get_replica_set_client(self):
#         return MongoClient(self.replica_set_uri, serverSelectionTimeoutMS=1000)

#     def is_ready(self):
#         ready = False
#         client = self.get_client()
#         try:
#             client.server_info()
#             ready = True
#             logger.debug("mongodb service is ready.")
#         except ServerSelectionTimeoutError:
#             logger.debug("mongodb service is not ready yet.")
#         finally:
#             client.close()
#         return ready

#     def reconfigure_replica_set(self, hosts: list):
#         replica_set_client = self.get_replica_set_client()
#         try:
#             rs_config = replica_set_client.admin.command("replSetGetConfig")
#             rs_config["config"]["_id"] = self.replica_set_name
#             rs_config["config"]["members"] = [
#                 {"_id": i, "host": h} for i, h in enumerate(hosts)
#             ]
#             rs_config["config"]["version"] += 1
#             replica_set_client.admin.command(
#                 "replSetReconfig", rs_config["config"], force=True
#             )
#         except Exception as e:
#             logger.error(f"cannot reconfigure replica set. error={e}")
#         finally:
#             replica_set_client.close()

#     def initialize_replica_set(self, hosts: list):
#         config = {
#             "_id": self.replica_set_name,
#             "members": [{"_id": i, "host": h} for i, h in enumerate(hosts)],
#         }
#         client = self.get_client()
#         try:
#             logger.debug(f"initializing replica set with config={config}")
#             client.admin.command("replSetInitiate", config)
#         except Exception as e:
#             logger.error(f"cannot initialize replica set. error={e}")
#         finally:
#             client.close()
