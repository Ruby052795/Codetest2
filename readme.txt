Task 2: book.{instrument_name}.{depth}

1, Description
Python+BDD for WebSocket API: book.{instrument_name}.{depth}

*************************************************************************
3, Setup Guides
3.1 Clone the repository
git clone git@github.com:Ruby052795/Codetest2.git

3.2 Environment
    Python 3.10
    pip install -r requirements.txt

3.3 Test Case/Test Data Location
    /features/ws_orderbook.feature


3.4 Run Test
    # run all feature file
    behave
    # run specific feature file
    behave features/ws_orderbook.feature


3.4 Test Report
    # Allure should be properly configured on your local machine
    behave --format allure_behave.formatter:AllureFormatter -o allure-results -v --no-capture

    # Allure report should be generated and opened automatically . [after_all setup in environment.py]
    # If doesn't work, use below commend to generate allure report manually
    allure generate allure-results -o allure-report --clean
    allure open allure-report

**************************************************************************
