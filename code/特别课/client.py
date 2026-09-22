import requests
r = requests.get("https://wttr.in/%E6%B7%B1%E5%9C%B3?format=j1")
print(r.status_code)
if r.status_code == 200:
    try:
        print(r.headers["Content-Type"])
        data = r.json()
        print(type(data))
        print(len(data))
        print(data["current_condition"][0]["temp_C"])
    except Exception as e:
        print("错误：",e)