import sys
import json

if __package__:
    from .slate_base import api
else:
    from slate_base import api


def main(in_args=None):
    data_arg = in_args[-1]
    in_data = json.loads(data_arg)
    api.slate_generator(
        in_data["fill_data"],
        in_data.get("slate_data"),
        in_data.get("data_output_json")
    )


if __name__ == "__main__":
    main(sys.argv)
