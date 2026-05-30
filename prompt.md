etf_list.xlsx is the file that contains the list of ETFs (Exchange-Traded Funds) that we are interested in analyzing. I want you to 
pull historic price data for Region=EMEA ETFs from this file. You should use justetf-scraping/notebooks as examples. Create a new notebook and write code to read the etf_list.xlsx file, filter for Region=EMEA ETFs, and then pull historic price data for those ETFs using the justetf-scraping library.

each ETF's historic price data should be stored in a separate DataFrame and write to etf-data/ folder, with ISIN as its name ( E.g. IE00B2NPKV68.pkl) and you can should to save these DataFrames as CSV files for later analysis. 
The python env you should use is conda activate py313

I have already installed justetf-scraping via pip install git+https://github.com/druzsan/justetf-scraping.git, you should be able to import justetf_scraping directly in your code.
The python env you should use is conda activate py313

---

etf_list.xlsx is the file that contains the list of ETFs (Exchange-Traded Funds) that we are interested in analyzing. I want you to 
pull meta data for Region=EMEA ETFs from this file. You should use justetf-scraping/notebooks as examples. Create a new notebook and write code to read the etf_list.xlsx file, filter for Region=EMEA ETFs, and then pull metadata (or any other non price info) for those ETFs using the justetf-scraping library. As i have already pulled price data and downloaded to etf-data-gbp


each ETF's meta data should be stored in a separate json and write to etf-metadata-gbp/ folder, with ISIN as its name ( E.g. IE00B2NPKV68.json) and you can should to save these DataFrames as CSV files for later analysis. 
The python env you should use is conda activate py313

I have already installed justetf-scraping via pip install git+https://github.com/druzsan/justetf-scraping.git, you should be able to import justetf_scraping directly in your code.
The python env you should use is conda activate py313

-----
Use price data in etf-data-gbp/* (ETF Data in GBP), Come up with a strategy that trades once a month to select 1 ETF to trade and hold for 1 month. Backtest for all historical data. You can try momentum or other strategy ideas you deem good. Please keep trying until you find a strategy that sharpe > 1.5, it must be profitable in more than 90% of the historical years. Max drawdown should be less than 10%. Write the result to a notebook. etf-metadata-gbp/* contains metadata for the ETFs
you cannot trade or vol scale within 1 month, you can only adjust position once a month
The python env you should use is conda activate py313
