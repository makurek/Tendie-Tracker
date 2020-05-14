from cs50 import SQL
from flask import request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash


# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///budget.db")


# Get the users account name
def getUsername(userID):
    name = db.execute(
        "SELECT username FROM users WHERE id = :usersID", usersID=userID)

    return name[0]["username"]


# Get the users total income
def getIncome(userID):
    income = db.execute(
        "SELECT income FROM users WHERE id = :usersID", usersID=userID)

    return income[0]["income"]


# Update the users income
def updateIncome(income, userID):
    rows = db.execute("UPDATE users SET income = :newIncome WHERE id = :usersID",
                      newIncome=income, usersID=userID)

    # Return an error message if the record could not be updated
    if rows != 1:
        return {"apology": "Sorry, Update Income is angry. Try again!"}
    else:
        return rows


# Get the users payers
def getPayers(userID):
    payers = db.execute(
        "SELECT name FROM payers WHERE user_id = :usersID ORDER BY name ASC", usersID=userID)

    return payers


# Add a payer to the users account
def addPayer(name, userID):

    # Make sure the user has no more than 5 payers (note: this max amount is arbitrary, 5 sounded good ¯\_(ツ)_/¯)
    if getTotalPayers(userID) >= 5:
        return {"apology": "You have the maximum number of payers. Try deleting one you aren't using or contact the admin."}

    # Make sure the new payer does not already exist in the DB
    if payerExistsForUser(name, userID):
        return {"apology": "You already have a payer with that name. Enter a new, unique name."}
    else:
        # Insert new payer into DB
        db.execute("INSERT INTO payers (user_id, name) VALUES (:usersID, :name)",
                   usersID=userID, name=name)
        # TODO lazy fix to make the return type consistent with rename/delete payer and updateincome.
        # These functions return the # of rows updated/deleted (always being 1) whereas this one is using INSERT and returns the PK value. For now just return the value of 1 as a workaround.
        return 1


# Rename a users existing payer
def renamePayer(existingName, newName, userID):
    # Make sure the existing name actually exists in the DB
    if not payerExistsForUser(existingName, userID):
        return {"apology": "The payer you're trying to rename does not exist."}

    # Make sure the new name does not already exist in the DB
    if payerExistsForUser(newName, userID):
        return {"apology": "You already have a payer with that name. Enter a new, unique name."}

    # Update existing *expense* records to usse the new name
    db.execute("UPDATE expenses SET payer = :name WHERE user_id = :usersID AND payer = :oldName",
               name=newName, usersID=userID, oldName=existingName)

    # Update the existing *payer* record with the new payers name
    rows = db.execute(
        "UPDATE payers SET name = :name WHERE user_id = :usersID AND name = :oldName", name=newName, usersID=userID, oldName=existingName)

    # Return an error message if the record could not be updated
    if rows != 1:
        return {"apology": "Sorry, Rename Payer is having problems. Try again!"}
    else:
        return rows


# Delete a users existing payer
def deletePayer(name, userID):
    # Make sure the existing name actually exists in the DB
    if not payerExistsForUser(name, userID):
        return {"apology": "The payer you're trying to delete does not exist."}

    # Delete the record
    rows = db.execute("DELETE FROM payers WHERE name = :name AND user_id = :usersID",
                      name=name, usersID=userID)

    # Return an error message if the record could not be deleted
    if rows != 1:
        return {"apology": "Sorry, Delete payer isn't working for some reason. Try again!"}
    else:
        return rows


# Update the users password
def updatePassword(oldPass, newPass, userID):
    # Ensure the current password matches the hash in the DB
    userHash = db.execute(
        "SELECT hash FROM users WHERE id = :usersID", usersID=userID)
    if not check_password_hash(userHash[0]["hash"], oldPass):
        return {"apology": "invalid password"}

    # Generate hash for new password
    hashedPass = generate_password_hash(newPass)

    # Update the users account to use the new password hash
    rows = db.execute("UPDATE users SET hash = :hashedPass WHERE id = :usersID",
                      hashedPass=hashedPass, usersID=userID)

    # Return an error message if the password could not be updated
    if rows != 1:
        return {"apology": "Sorry, Update Password is having issues. Try again!"}
    else:
        return rows


# Check to see if the payer name passed in exists in the DB or not
def payerExistsForUser(payerName, userID):
    # 'Self' always returns true / exists because it's the default payer name used for the user
    if payerName.lower() == 'self':
        return True

    # Query the DB
    count = db.execute(
        "SELECT COUNT(*) AS 'count' FROM payers WHERE user_id = :usersID AND LOWER(name) = :name", usersID=userID, name=payerName.lower())

    if count[0]["count"] > 0:
        return True
    else:
        return False


# Get the users statistics
def getStatistics(userID):

    # Create a data structure to hold statistics
    stats = {"registerDate": None, "totalExpenses": None,
             "totalBudgets": None, "totalCategories": None, "totalPayers": None}

    # Get registration date
    registerDate = db.execute(
        "SELECT registerDate FROM users WHERE id = :usersID", usersID=userID)
    stats["registerDate"] = registerDate[0]["registerDate"].split()[0]

    # Get total expenses
    totalExpenses = db.execute(
        "SELECT COUNT(*) AS 'count' FROM expenses WHERE user_id = :usersID", usersID=userID)
    stats["totalExpenses"] = totalExpenses[0]["count"]

    # Get total budgets
    totalBudgets = db.execute(
        "SELECT COUNT(*) AS 'count' FROM budgets WHERE user_id = :usersID", usersID=userID)
    stats["totalBudgets"] = totalBudgets[0]["count"]

    # Get total categories
    totalCategories = db.execute(
        "SELECT COUNT(*) AS 'count' FROM userCategories INNER JOIN categories ON userCategories.category_id = categories.id WHERE userCategories.user_id = :usersID",
        usersID=userID)
    stats["totalCategories"] = totalCategories[0]["count"]

    # Get total payers
    totalPayers = getTotalPayers(userID)
    stats["totalPayers"] = totalPayers

    return stats


# Get a count of the total number of payers a user has
def getTotalPayers(userID):
    count = db.execute(
        "SELECT COUNT(*) AS 'count' FROM payers WHERE user_id = :usersID", usersID=userID)

    return count[0]["count"]


# Get all of the users account info for their 'Your Account' page
def getAllUserInfo(userID):

    # Create dict to hold user info
    user = {"name": None, "income": None, "payers": None, "stats": None}

    # Get the users account name
    user["name"] = getUsername(userID)

    # Get the users income
    user["income"] = getIncome(userID)

    # Get users payers
    user["payers"] = getPayers(userID)

    # Get the users stats
    user["stats"] = getStatistics(userID)

    return user
