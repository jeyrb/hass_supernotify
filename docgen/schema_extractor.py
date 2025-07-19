import sys
from pathlib import Path

sys.path.append(str((Path(__file__).parent / "..").resolve()))

import inspect
import json
import logging

import homeassistant.helpers.config_validation as cv
import jsonschema_markdown
import mkdocs_gen_files
from voluptuous import Any, Schema
from voluptuous_openapi import convert

import custom_components.supernotify

# some hacks to stop voluptuous_openapi generating broken schemas


def tune_schema(node: dict | list) -> None:
    if isinstance(node, dict):
        for key in node:
            if node[key] in (cv.url, cv.string):
                node[key] = str
                logging.info(f"Converted {key} to Required(str)")
            if isinstance(node[key], Any):
                node[key].validators = [v if v not in (cv.url, cv.string) else str for v in node[key].validators]


def walk_schema(schema: dict | list) -> None:
    tune_schema(schema)
    if isinstance(schema, dict):
        for key in schema:
            walk_schema(schema[key])
    elif isinstance(schema, list):
        for sub_schema in schema:
            walk_schema(sub_schema)


def schema_doc(debug: bool = False) -> None:
    # Path("docs/schemas").mkdir(exist_ok=True)

    v_schemas = {m[0]: m[1] for m in inspect.getmembers(custom_components.supernotify, lambda m: isinstance(m, Schema))}
    for schema_name in v_schemas:
        walk_schema(v_schemas[schema_name].schema)
    j_schemas = {s[0]: convert(s[1]) for s in v_schemas.items()}

    # parser = jsonschema2md.Parser(collapse_children=True)
    for schema_name, schema in j_schemas.items():
        try:
            schema.setdefault("title", schema_name)
            schema.setdefault("$id", "https://jeyrb.github.io/hass_supernotify/schemas/" + schema_name + ".json")
            schema.setdefault("description", f"Voluptuous Validation Schema for {schema_name}")
            schema.setdefault("$schema", "https://json-schema.org/draft/2020-12/schema")
            if debug:
                with mkdocs_gen_files.open(f"schemas/{schema_name}.json", "w") as f:
                    json.dump(schema, f, indent=2, ensure_ascii=False)

            lines = jsonschema_markdown.generate(schema, hide_empty_columns=True, replace_refs=True)

            with mkdocs_gen_files.open(f"schemas/{schema_name}.md", "w") as f:
                f.write(lines)

        except Exception as e:
            logging.warning(f"Error processing schema {schema_name}: {e}")
            continue


schema_doc()
