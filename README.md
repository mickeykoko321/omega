# Omega Package

**Important:** Before using, please make sure to update the file **omega.config** at the root of the omega folder. 
This file contains paths to the relevant folders that are used throughout the application.

What needs to be updated (everything else should not need to be updated):
* default/root: Set this to the root of the omega folder (where the package is)
* default/data: Root where the data is stored
* default/database: Set this where the database.json file is
* logging/root: Where the log are written

Also, PYTHONPATH needs to be added to the User Environment Variables with the root of where all the packages are
installed (as an example for my config: C:\Users\Laurent\OneDrive\Trading\Omega).


See below for some tasks that this module is trying to achieve.

### 1. Cabbage:
Anything related to risk for the strategies (might not really be needed for now as only 2 functions). And also some
tests on a Libor-FF forecast (which were unsuccessful so far). This will need some work.

### 2. Core:
* Chain: Provides definition and helper functions for a Future's chain.
* Chart: Some basic charts using HighCharts. Consider moving this somewhere else.
* Instrument: This module needs refactoring as at the moment is an aggregate of several different types of code all
related to an instrument. Examples: FutureType Enum, way to deal with maturities, ticker conversion, etc...
* Lists: This is to create lists of tickers for download or for the Quotes' sheets.

### 3. Data:
* Historical Data Download: Download from Reuters.
For the download, we need to download data for active contracts on a daily basis. We also need to download
historical data for expired contracts when we build the database (or our own history) for backtests. This is
important as in the future we might add symbols on the fly (or re-download history for certain markets).
We also need to re-download the last few days of a contract that has just expired. This is a not well implemented
area that probably needs some work (we potentially could use an extra status called: ActivePlus?).
* Get COT Data from Quandl. We will also have to add functions to get data from the ICE website.
* The module lists is a helper for this (Idea: Move daily differences somewhere else)?
* We also need to make basic operations with data: Get/Save Data, transformations (roll yield), etc...

### 4. Logger:
Logging module and its configuration.

### 5. Xl:
Anything that interacts with excel for the spreading and curvature strategies. Higher-level functionalities:
* Update Risk (Both)
* Populate Quotes sheet (Both)
* Refresh positions sheet (Curvature)
* Snap Quotes (Curvature)
* Get Trades (Curvature)
* Get Universe (Spreading)