import json
import requests

def fetch_gameweeks():
    url = "https://api.sorare.com/graphql"
    query = """
    query{
    	so5{
        allSo5Fixtures(sport:FOOTBALL,eventType:CLASSIC){
          nodes{
            shortDisplayName
            startDate
            endDate
            timeZone
          }
        }
      }
    }
    """

    response = requests.post(url, json={"query": query})
    response.raise_for_status()
    data = response.json()

    fixtures = data["data"]["so5"]["allSo5Fixtures"]["nodes"]

    # Convert to list of dicts with proper datetime format
    gameweeks = [
        {
            "gw": fixture["shortDisplayName"],
            "startDate": fixture["startDate"],
            "endDate": fixture["endDate"],
            "timeZone": fixture["timeZone"],
        }
        for fixture in fixtures
    ]

    # Save to JSON file
    output_file = "config/gameweeks.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(gameweeks, f, indent=2, ensure_ascii=False)
    
    message=f"✅ Gameweeks saved to {output_file}"

    return message