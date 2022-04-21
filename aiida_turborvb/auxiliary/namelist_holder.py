from typing import ( Optional, Any )

class NamelistHolder:

    def __init__(self, name):
        self.name = name
        self.values = []

    def add_value(self,
                  name: str,
                  type_: type,
                  value : Any = None,
                  hidden : Optional[bool] = False ):
        """
        Add one value into the namelist
        """

        if not isinstance(value, type_):
            # TODO
            raise Exception()

        val = { "name"   : name,
                "type"   : type_,
                "value"  : value,
                "hidden" : hidden }

        self.values.append(val)

    def dump(self, handle):
        handle.write(f"&{self.name}\n")
        for entry in self.values:
            if entry['type'] == bool:
                val = f"{'.TRUE.' if entry['value'] else '.FALSE.'}"
            if entry['type'] == str:
                val = f"'{entry['value']}'"
            else:
                val = str(entry['type'](entry['value']))
            handle.write(f" {'!' if entry['hidden'] else ' '}{entry['name']} = {val}\n")
        handle.write(f"/\n")

    def update(self, key : str, value : Any):
        for ii, entry in enumerate(self.values):
            if entry["name"] == key:
                if not isinstance(value, entry["type"]):
                    # TODO
                    raise Exception()
                if entry["hidden"]:
                    self.value[ii]["hidden"] = False
                self.values[ii]["value"] = value
                return
        raise Exception()

    def get_keys(self):
        return [ x["name"] for x in self.values ]
