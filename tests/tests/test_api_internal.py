#!/usr/bin/python
# Copyright 2016 Mender Software AS
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        https://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
import os
from common import internal_client, management_client, mongo, clean_db, inventory_attributes
import bravado
import pytest

class TestInternalApiTenantCreate:
    def test_create_ok(self, internal_client, clean_db):

        _, r = internal_client.create_tenant('foobar')
        assert r.status_code == 201

        assert 'inventory-foobar' in clean_db.database_names()
        assert 'migration_info' in clean_db['inventory-foobar'].collection_names()

    def test_create_twice(self, internal_client, clean_db):

        _, r = internal_client.create_tenant('foobar')
        assert r.status_code == 201

        # creating once more should not fail
        _, r = internal_client.create_tenant('foobar')
        assert r.status_code == 201


    def test_create_empty(self, internal_client):
        try:
            _, r = internal_client.create_tenant('')
        except bravado.exception.HTTPError as e:
            assert e.response.status_code == 400


class TestInternalApiDeviceCreate:
    def test_create_ok(self, internal_client, management_client, clean_db, inventory_attributes):
        devid = "".join([ format(i, "02x") for i in os.urandom(128)])
        _, r = internal_client.create_device(device_id = devid,
                                             attributes=inventory_attributes)
        assert r.status_code == 201

        r, _ = management_client.client.devices.get_devices_id(id=devid,
                                                               Authorization="foo").result()

        self._verify_inventory(inventory_attributes,
                              [internal_client.Attribute(name=attr.name,
                                                         value=attr.value,
                                                         description=attr.description) for attr in r.attributes])

    def test_create_twice_ok(self, internal_client, management_client, clean_db, inventory_attributes):
        # insert first device
        devid = "".join([ format(i, "02x") for i in os.urandom(128)])
        _, r = internal_client.create_device(device_id = devid,
                                             attributes=inventory_attributes)
        assert r.status_code == 201

        # add extra attribute, modify existing
        new_attr = internal_client.Attribute(name="new attr",
                                             value="new value",
                                              description="desc")

        existing = inventory_attributes[0]
        existing.value = "newval"
        existing.description = "newdesc"

        new_attrs = [new_attr, existing]

        # inventory_attributes will now act as 'expected' output attrs
        inventory_attributes.append(new_attr)

        # insert 'the same' device
        _, r = internal_client.create_device(device_id = devid,
                                             attributes=new_attrs)
        assert r.status_code == 201

        # verify update
        r, _ = management_client.client.devices.get_devices_id(id=devid,
                                                               Authorization="foo").result()

        self._verify_inventory(inventory_attributes, r.attributes)

    def _verify_inventory(self, expected, inventory):
         assert len(inventory) == len(expected)

         print("inventory:\n", inventory, "expected:\n", expected)
         for e in expected:
            found = [f for f in inventory if (f.name == e.name and f.value == e.value and f.description==e.description)]
            assert len(found)==1, "Inventory data is incorrect"
