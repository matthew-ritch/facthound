"""
Blockchain verification utilities for the questions app.

This module provides functions to verify and synchronize on-chain data with the database.
It handles confirmation of questions, answers, and answer selections by checking the 
FactHound contract's state on-chain and updating the corresponding database objects accordingly.
"""

import os
from web3 import Web3
import json
import hexbytes
import logging

from siweauth.models import User
from questions.models import Question, Answer
from questions.settings import allowed_owners

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logging.basicConfig(
    filename="facthound.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

w3 = Web3(
    Web3.HTTPProvider(
        f"{os.getenv('ALCHEMY_API_ENDPOINT')}/{os.getenv('ALCHEMY_API_KEY')}"
    )
)
with open("contracts/FactHound.json", "rb") as f:
    facthound_contract = json.load(f)
facthound_abi = facthound_contract["abi"]
facthound_bytecode = facthound_contract["bytecode"]["object"]


def confirm_question(questionHash):
    """
    Confirm a question's on-chain status and update local database accordingly.
    
    This function verifies that a question exists on-chain with the provided hash,
    checks the contract ownership, and updates the database record with on-chain data.
    
    Args:
        questionHash (hexbytes.HexBytes): The hash of the question to confirm
        
    Returns:
        tuple: (success_bool, response_message_or_dict)
            - success_bool: True if confirmation succeeded, False otherwise
            - response_message_or_dict: Success message/data or error message
            
    Note:
        This updates the question's status, asker, bounty, and confirmed_onchain flag
        in the database if successful.
    """
    try:
        question = Question.objects.get(questionHash=questionHash)
    except Question.DoesNotExist:
        return False, "Question not found."
    try:
        contract = w3.eth.contract(
            address=question.contractAddress, abi=facthound_abi, decode_tuples=True
        )
        owner = contract.caller.owner()
    except:
        return False, "Failed to load contract."
    # verify that we own this contract
    if not owner in allowed_owners:
        return False, "Invalid owner."
    expectedQuestionHash = Web3.solidity_keccak(
        ["address", "string"], [question.asker.wallet, question.post.text]
    )
    questionStruct = contract.caller.getQuestion(question.questionHash)
    asker = questionStruct.asker
    if question.questionHash != expectedQuestionHash:
        return False, "Unexpected questionHash."
    asker, _ = User.objects.get_or_create(wallet=asker)
    bounty = questionStruct.bounty
    status = (
        "CA"
        if questionStruct.status == 4
        else (
            "RS"
            if questionStruct.status == 3
            else ("AS" if (questionStruct.status == 1) else "OP")
        )
    )
    # passed. update
    question.asker = asker
    question.bounty = bounty
    question.status = status
    question.confirmed_onchain = True
    question.save()
    return True, {"message": "Success", "thread": question.post.thread.pk}


def confirm_answer(questionHash, answerHash):
    """
    Confirm an answer's on-chain status and update local database accordingly.
    
    This function verifies that an answer exists on-chain with the provided hash,
    checks the contract ownership, verifies the answer hash matches the expected value,
    and updates the database record with on-chain data.
    
    Args:
        questionHash (hexbytes.HexBytes): The hash of the question being answered
        answerHash (hexbytes.HexBytes): The hash of the answer to confirm
        
    Returns:
        tuple: (success_bool, response_message_or_dict)
            - success_bool: True if confirmation succeeded, False otherwise
            - response_message_or_dict: Success message/data or error message
            
    Note:
        This updates the answer's status, answerer, and confirmed_onchain flag
        in the database if successful.
    """
    try:
        answer = Answer.objects.get(answerHash=answerHash)
        question = answer.question
    except Answer.DoesNotExist:
        return False, "Answer not found."
    try:
        contract = w3.eth.contract(
            address=question.contractAddress, abi=facthound_abi, decode_tuples=True
        )
        owner = contract.caller.owner()
    except:
        return False, "Failed to load contract."
    # verify that we own this contract
    if not owner in allowed_owners:
        return False, "Invalid owner."
    expectedAnswerHash = Web3.solidity_keccak(
        ["address", "string"], [answer.answerer.wallet, answer.post.text]
    )
    answerHash = hexbytes.HexBytes(answer.answerHash)
    if answerHash != expectedAnswerHash:
        return False, "Unexpected answerHash"
    # verify that answerHash is an answer for this contract and was posted by this answerer
    questionStruct = contract.caller.getQuestion(answer.question.questionHash)
    answerer = contract.caller.getAnswererAddress(
        answer.question.questionHash, answerHash
    )
    if answerer == ("0x" + 40 * "0"):
        return False, "Invalid answerHash"
    answerer, _ = User.objects.get_or_create(
        wallet=answerer
    )
    status = (
        "SE" if answerHash == questionStruct.selectedAnswer.hex() else "UN"
    )  # TODO get other states in here
    confirmed_onchain = True
    # passed. update
    answer.answerer = answerer
    answer.status = status
    answer.confirmed_onchain = confirmed_onchain
    answer.save()
    return True, {"message": "Success", "thread": question.post.thread.pk}


def confirm_selection(questionHash, answerHash):
    """
    Confirm an answer selection's on-chain status and update local database accordingly.
    
    This function verifies that an answer has been selected on-chain for the given question,
    and updates the database record with the selection status.
    
    Args:
        questionHash (hexbytes.HexBytes): The hash of the question
        answerHash (hexbytes.HexBytes): The hash of the answer to confirm selection
        
    Returns:
        tuple: (success_bool, response_message_or_dict)
            - success_bool: True if confirmation succeeded, False otherwise
            - response_message_or_dict: Success message/data or error message
            
    Note:
        This updates the answer's selection_confirmed_onchain flag and status
        in the database if successful.
    """
    try:
        answer = Answer.objects.get(answerHash=answerHash)
        question = answer.question
    except Answer.DoesNotExist:
        return False, "Answer not found."
    try:
        contract = w3.eth.contract(
            address=question.contractAddress, abi=facthound_abi, decode_tuples=True
        )
        owner = contract.caller.owner()
    except:
        return False, "Failed to load contract."

    # make sure this answer was selected in the contract
    questionStruct = contract.caller.getQuestion(question.questionHash)
    selectedAnswer = questionStruct.selectedAnswer
    if selectedAnswer != answer.answerHash:
        answer.status = "UN"
        answer.selection_confirmed_onchain = False
        answer.save()
        return False, f"This answer must be selected in the contract at address {question.contractAddress}."
    selection_confirmed_onchain = True
    # passed. update
    answer.selection_confirmed_onchain = selection_confirmed_onchain
    answer.save()
    return True, {"message": "Success", "thread": question.post.thread.pk}
