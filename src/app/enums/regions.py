from enum import Enum


class OpenLabsRegion(Enum):
    """OpenLabs supported cloud regions."""

    US_EAST_1 = "us_east_1"
    US_EAST_2 = "us_east_2"


AWS_REGION_MAP = {
    # https://docs.aws.amazon.com/global-infrastructure/latest/regions/aws-regions.html
    OpenLabsRegion.US_EAST_1: "us-east-1",  # Virgina
    OpenLabsRegion.US_EAST_2: "us-east-2",  # Ohio
}

AZURE_REGION_MAP = {
    # https://gist.github.com/ausfestivus/04e55c7d80229069bf3bc75870630ec8
    OpenLabsRegion.US_EAST_1: "eastus",
    OpenLabsRegion.US_EAST_2: "eastus2",
}
