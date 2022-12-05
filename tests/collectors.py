# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest
import yaml

from .fixtures import plan_summary, plan_validator


class FabricTestFile(pytest.File):

  def collect(self):
    """Read yaml test spec and yield test items for each test definition.

    Test spec should contain a `module` key with the path of the
    terraform module to test, relative to the root of the repository

    All other top-level keys in the yaml are taken as test names, and
    should have the following structure:

    test-name:
      tfvars:
        - tfvars1.tfvars
        - tfvars2.tfvars
      inventory:
        - inventory1.yaml
        - inventory2.yaml

    All paths specifications are relative to the location of the test
    spec. The inventory key is optional, if omitted, the inventory
    will be taken from the file test-name.yaml

    """
    try:
      raw = yaml.safe_load(self.path.open())
      module = raw.pop('module')
    except (IOError, OSError, yaml.YAMLError) as e:
      raise Exception(f'cannot read test spec {self.path}: {e}')
    except KeyError as e:
      raise Exception(f'`module` key not found in {self.path}: {e}')
    for test_name, spec in raw.items():
      inventories = spec.get('inventory', [f'{test_name}.yaml'])
      try:
        tfvars = spec['tfvars']
      except KeyError:
        raise Exception(
            f'test definition `{test_name}` in {self.path} does not contain a `tfvars` key'
        )
      for i in inventories:
        name = test_name
        if isinstance(inventories, list) and len(inventories) > 1:
          name = f'{test_name}[{i}]'
        yield FabricTestItem.from_parent(self, name=name, module=module,
                                         inventory=[i], tfvars=tfvars)


class FabricTestItem(pytest.Item):

  def __init__(self, name, parent, module, inventory, tfvars):
    super().__init__(name, parent)
    self.module = module
    self.inventory = inventory
    self.tfvars = tfvars

  def runtest(self):
    s = plan_validator(self.module, self.inventory, self.parent.path.parent,
                       self.tfvars)

  def reportinfo(self):
    return self.path, None, self.name


def pytest_collect_file(parent, file_path):
  'Collect tftest*.yaml files and run plan_validator from them.'
  if file_path.suffix == '.yaml' and file_path.name.startswith('tftest'):
    return FabricTestFile.from_parent(parent, path=file_path)
