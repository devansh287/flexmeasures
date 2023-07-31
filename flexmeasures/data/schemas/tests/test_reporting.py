from flexmeasures.data.schemas.reporting.pandas_reporter import (
    PandasReporterConfigSchema,
)
from marshmallow.exceptions import ValidationError

import pytest


@pytest.mark.parametrize(
    "reporter_config, is_valid",
    [
        (
            {  # this checks that the final_df_output dataframe is actually generated at some point of the processing pipeline
                "beliefs_search_configs": [
                    {
                        "sensor": 1,
                        "event_starts_after": "2022-01-01T00:00:00 00:00",
                        "event_ends_before": "2022-01-01T23:00:00 00:00",
                    },
                ],
                "transformations": [
                    {
                        "df_output": "final_output",
                        "df_input": "sensor_1",
                        "method": "copy",
                    }
                ],
                "final_df_output": "final_output",
            },
            True,
        ),
        (
            {  # this checks that chaining works, applying the method copy on the previous dataframe
                "beliefs_search_configs": [
                    {
                        "sensor": 1,
                        "event_starts_after": "2022-01-01T00:00:00 00:00",
                        "event_ends_before": "2022-01-01T23:00:00 00:00",
                    },
                ],
                "transformations": [
                    {"df_output": "output1", "df_input": "sensor_1", "method": "copy"},
                    {"method": "copy"},
                    {"df_output": "final_output", "method": "copy"},
                ],
                "final_df_output": "final_output",
            },
            True,
        ),
        (
            {  # this checks that resample cannot be the last method being applied
                "beliefs_search_configs": [
                    {
                        "sensor": 1,
                        "event_starts_after": "2022-01-01T00:00:00 00:00",
                        "event_ends_before": "2022-01-01T23:00:00 00:00",
                    },
                    {
                        "sensor": 2,
                        "event_starts_after": "2022-01-01T00:00:00 00:00",
                        "event_ends_before": "2022-01-01T23:00:00 00:00",
                    },
                ],
                "transformations": [
                    {"df_output": "output1", "df_input": "sensor_1", "method": "copy"},
                    {"method": "copy"},
                    {"df_output": "final_output", "method": "resample", "args": ["1h"]},
                ],
                "final_df_output": "final_output",
            },
            False,
        ),
        (
            {  # this checks that resample cannot be the last method being applied
                "beliefs_search_configs": [
                    {
                        "sensor": 1,
                        "event_starts_after": "2022-01-01T00:00:00 00:00",
                        "event_ends_before": "2022-01-01T23:00:00 00:00",
                    },
                    {
                        "sensor": 2,
                        "event_starts_after": "2022-01-01T00:00:00 00:00",
                        "event_ends_before": "2022-01-01T23:00:00 00:00",
                    },
                ],
                "transformations": [
                    {"df_output": "output1", "df_input": "sensor_1", "method": "copy"},
                    {"method": "copy"},
                    {"df_output": "final_output", "method": "resample", "args": ["1h"]},
                    {"method": "sum"},
                ],
                "final_df_output": "final_output",
            },
            True,
        ),
    ],
)
def test_pandas_reporter_schema(
    reporter_config, is_valid, db, app, setup_dummy_sensors
):

    schema = PandasReporterConfigSchema()

    if is_valid:
        schema.load(reporter_config)
    else:
        with pytest.raises(ValidationError):
            schema.load(reporter_config)
