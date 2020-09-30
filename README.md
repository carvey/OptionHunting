# Option Hunting
![logo](optionHunter.PNG)
## Setup Instructions

This project was written on python 3.7.3. Anything before or after that could have some quirks.

1) Install the TD ameritrade API with PIP (lookup how to install pip on your OS if you don't have it installed): 
    ```
    pip3 install -r requirements.txt
    ```
2) Go to https://developer.tdameritrade.com and sign up for a seperate account there
3) Create a new app on here. Make up some values for all the fields except "Callback URL" which should be set to "http://localhost"
4) Take the consumer key for that application and put it in a file called "tda.txt" that's in the same directory as all the other files in this project.
5) Next up is making an "Option Hunting" (see parameters.txt) watchlist for the script to scan. Open up **TD Ameritrade web or your-non paper money thinkorswim account to do this. The TD Ameritrade API will not be able to scan a watchlist that was set up on a paper money account.** Throw a bunch of **high quality stocks and ETFs** in there. This script searches for bullish positions, so lean towards stocks that have a long history of trending upwards. The script has been tested to work with about 145 stocks but isn't guaranteed to work with more due to rumored rate limit issues with the API.
7) Open up parameters.txt and edit those values as necessary. The only necessary one to edit is "watchlist" and should be set to whatever TD Ameritrade watchlist you want to scan. The other parameters are the defaults I'm using for the time being.

## Generating an Excel Sheet
Run the program with the following command. Note that the first time you run this will cause a login screen to pop up and will give you a weird error page with a localhost link you have to paste back in the terminal. That step is confusing and can be glitchy but you shouldn't have to do it too often.
   ```
   python3 excel.py
   ```
### TD Ameritrade Auth Error 
During first run of `excel.py` the `creds.txt` file is not populated and you will need to authenticate without a web server, hence the "http://localhost" above. `excel.py` will generate a url for you to browse IOT authenticate (see example 1 below). If tdameritrade throws an error (`A third-party application may be attempting to make unauthorized...`), then try Example 2.    

Example 1: 
   ```
	https://auth.tdameritrade.com/auth?response_type=code&redirect_uri=https%3A%2F%2F127.0.0.1&client_id=EXAMPLE%40AMER.OAUTHAP
   ```
Example 2: 
   ```
	https://auth.tdameritrade.com/oauth?client_id=EXAMPLE%40AMER.OAUTHAP&response_type=code&redirect_uri=http%3A%2F%2Flocalhost
   ```	
