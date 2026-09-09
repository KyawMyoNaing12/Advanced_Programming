import pytest
from unittest.mock import Mock

from Sale_Data_Validation import FilePanel


@pytest.fixture
def validator():
    """
    Create FilePanel without starting the Tkinter GUI.
    """
    panel = FilePanel.__new__(FilePanel)

    panel.app = Mock()
    panel.app.log_message = Mock()

    panel.file_tree = Mock()
    panel.ftp_manager = Mock()

    return panel


@pytest.fixture
def valid_filename():
    """Return a valid filename."""
    return "SALES_DATA_20260730100000.csv"


@pytest.fixture
def valid_csv():
    """Return valid CSV content."""
    return (
        "transaction_id,timestamp,store_id,product_id,"
        "quantity,unit_price,total_amount,payment_method\n"
        "TX001,2026-07-30 10:00:00,S001,P001,"
        "2,10,20,cash\n"
    )


@pytest.fixture
def ftp_client(valid_csv):
    """
    Create a mock FTP client that returns
    valid CSV data.
    """
    client = Mock()

    def download_file(command, callback):
        callback(valid_csv.encode("utf-8"))

    client.retrbinary.side_effect = download_file

    return client


@pytest.fixture
def selected_file(
    validator,
    valid_filename,
    ftp_client
):
    """
    Configure a complete valid file scenario.

    This fixture configures:
    1. Selected Treeview item
    2. Filename
    3. Active FTP connection
    4. FTP client
    5. Valid CSV data
    """

    # Select a file in Treeview
    validator.file_tree.selection.return_value = (
        "item1",
    )

    # IMPORTANT:
    # The application uses:
    # self.file_tree.item(..., "values")[0]
    #
    # Therefore this must be a tuple/list,
    # NOT a dictionary.
    validator.file_tree.item.return_value = (
        valid_filename,
    )

    # FTP connection is active
    validator.ftp_manager.is_connected.return_value = True

    # Return mock FTP client
    validator.ftp_manager.get_client.return_value = (
        ftp_client
    )

    return validator


def set_selected_filename(validator, filename):
    """
    Change the selected filename in the mocked Treeview.
    """
    validator.file_tree.selection.return_value = ("item1",)

    validator.file_tree.item.return_value = (
        filename,
    )


def set_ftp_file(validator, file_content):
    """
    Configure the mocked FTP client to return file_content.
    """
    client = validator.ftp_manager.get_client.return_value

    def download_file(command, callback):
        callback(file_content.encode("utf-8"))

    client.retrbinary.side_effect = download_file


def test_valid_file(selected_file):
    """
    Test a correctly formatted and valid CSV file.
    """
    result = selected_file.validate_selected_file(
        silent=True
    )

    assert result == (True, "Passed")


def test_no_file_selected(validator):
    """
    Test validation when no file is selected.
    """
    validator.file_tree.selection.return_value = ()

    result = validator.validate_selected_file(
        silent=True
    )

    assert result == (
        False,
        "No file selected"
    )


def test_invalid_filename(
    validator,
    valid_filename
):
    """
    Test incorrect filename format.
    """
    set_selected_filename(
        validator,
        "sales_data.csv"
    )

    result = validator.validate_selected_file(
        silent=True
    )

    assert result[0] is False
    assert "Incorrectly formatted filename" in result[1]


def test_ftp_connection_inactive(
    selected_file
):
    """
    Test validation when FTP is disconnected.
    """
    selected_file.ftp_manager.is_connected.return_value = False

    result = selected_file.validate_selected_file(
        silent=True
    )

    assert result == (
        False,
        "FTP connection is inactive."
    )


def test_empty_file(
    selected_file
):
    """
    Test a 0-byte CSV file.
    """
    set_ftp_file(
        selected_file,
        ""
    )

    result = selected_file.validate_selected_file(
        silent=True
    )

    assert result[0] is False
    assert "empty (0-byte size)" in result[1]


def test_invalid_headers(
    selected_file
):
    """
    Test CSV with incorrect headers.
    """
    csv_data = (
        "id,date,product,price\n"
        "TX001,2026-07-30,P001,20\n"
    )

    set_ftp_file(
        selected_file,
        csv_data
    )

    result = selected_file.validate_selected_file(
        silent=True
    )

    assert result[0] is False
    assert "Missing or incorrectly named headers" in result[1]


def test_wrong_number_of_columns(
    selected_file
):
    """
    Test CSV row with incorrect number of columns.
    """
    csv_data = (
        "transaction_id,timestamp,store_id,product_id,"
        "quantity,unit_price,total_amount,payment_method\n"
        "TX001,2026-07-30,S001,P001,2,10,20\n"
    )

    set_ftp_file(
        selected_file,
        csv_data
    )

    result = selected_file.validate_selected_file(
        silent=True
    )

    assert result[0] is False
    assert "Column constraint mismatch" in result[1]


def test_empty_cell(
    selected_file
):
    """
    Test CSV containing an empty cell.
    """
    csv_data = (
        "transaction_id,timestamp,store_id,product_id,"
        "quantity,unit_price,total_amount,payment_method\n"
        "TX001,,S001,P001,2,10,20,cash\n"
    )

    set_ftp_file(
        selected_file,
        csv_data
    )

    result = selected_file.validate_selected_file(
        silent=True
    )

    assert result[0] is False
    assert "Empty cell value discovered" in result[1]


def test_duplicate_transaction_id(
    selected_file
):
    """
    Test duplicate transaction IDs.
    """
    csv_data = (
        "transaction_id,timestamp,store_id,product_id,"
        "quantity,unit_price,total_amount,payment_method\n"
        "TX001,2026-07-30,S001,P001,2,10,20,cash\n"
        "TX001,2026-07-30,S002,P002,1,15,15,cash\n"
    )

    set_ftp_file(
        selected_file,
        csv_data
    )

    result = selected_file.validate_selected_file(
        silent=True
    )

    assert result[0] is False
    assert "Duplicate transaction_id" in result[1]


def test_non_numeric_values(
    selected_file
):
    """
    Test quantity, price, or total containing text.
    """
    csv_data = (
        "transaction_id,timestamp,store_id,product_id,"
        "quantity,unit_price,total_amount,payment_method\n"
        "TX001,2026-07-30,S001,P001,two,10,20,cash\n"
    )

    set_ftp_file(
        selected_file,
        csv_data
    )

    result = selected_file.validate_selected_file(
        silent=True
    )

    assert result[0] is False
    assert "Non-numeric" in result[1]


def test_negative_values(
    selected_file
):
    """
    Test negative or zero numeric values.
    """
    csv_data = (
        "transaction_id,timestamp,store_id,product_id,"
        "quantity,unit_price,total_amount,payment_method\n"
        "TX001,2026-07-30,S001,P001,-2,10,-20,cash\n"
    )

    set_ftp_file(
        selected_file,
        csv_data
    )

    result = selected_file.validate_selected_file(
        silent=True
    )

    assert result[0] is False
    assert "valid positive numbers" in result[1]


def test_total_amount_calculation(
    selected_file
):
    """
    Test whether total_amount equals
    quantity * unit_price.
    """
    csv_data = (
        "transaction_id,timestamp,store_id,product_id,"
        "quantity,unit_price,total_amount,payment_method\n"
        "TX001,2026-07-30,S001,P001,2,10,25,cash\n"
    )

    set_ftp_file(
        selected_file,
        csv_data
    )

    result = selected_file.validate_selected_file(
        silent=True
    )

    assert result[0] is False
    assert "total_amount does not match calculation" in result[1]


def test_ftp_download_error(
    selected_file
):
    """
    Test FTP download exception.
    """
    client = selected_file.ftp_manager.get_client.return_value

    client.retrbinary.side_effect = Exception(
        "FTP download failed"
    )

    result = selected_file.validate_selected_file(
        silent=True
    )

    assert result[0] is False
    assert "Decoding/FTP error" in result[1]

