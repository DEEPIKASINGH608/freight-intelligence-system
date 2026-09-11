from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def get_routes():
    return {
        "routes": [
            {
                "origin": "Australia",
                "origin_port": "Port Hedland",
                "destination": "India",
                "destination_port": "Paradip",
                "distance_nautical_miles": 3850
            }
        ]
    }