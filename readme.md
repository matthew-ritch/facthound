# Facthound

**Facthound is a truth-seeking missile.** 

**Facthound is information bounties and information markets.**

**Facthound is the only forum that matters.**

## Overview

Facthound is an information bounty system where users ask questions and post optional bounties held in the Facthound escrow smart contract. Bounty posters pay out rewards to users who provide their preferred answers. While platforms like Quora and Reddit may refuse certain types of questions, Facthound's incentive-based model ensures virtually any question can be answered for the right price.

## Key Features

- **Information Bounties**: Post questions with ETH rewards for quality answers
- **Blockchain Integration**: Secure escrow system using smart contracts
- **Dual Authentication**: Traditional username/password or Ethereum wallet (SIWE) authentication
- **Answer Selection**: Question askers can select the best answer to receive the bounty
- **On-chain Verification**: Confirm questions, answers, and selections on the blockchain

## How It Works

1. **Ask a Question**: Users post questions with optional ETH bounties held in escrow
2. **Submit Answers**: Other users provide answers to earn the bounty
3. **Select Answer**: The question asker selects their preferred answer
4. **Payout**: The bounty is automatically released to the selected answerer

## This Repo

This repository contains Facthound's backend service built with Django. The backend provides API endpoints for the [frontend](https://github.com/matthew-ritch/facthound-frontend) and handles both on-chain and off-chain operations. On-chain operations are synced with the [Facthound](https://basescan.org/address/0x6F639b39606936F8Dfb82322781c913170b66f4f) contract. 

## Structure

### Questions App

The Questions app is responsible for:
- Tracking questions, answers, bounties, and their states
- Providing CRUD operations for forum content
- Handling on-chain verification of questions and answers
- Managing thread organization and tagging

### Siweauth App

The Siweauth app handles user authentication and authorization with:
- **Sign In With Ethereum (SIWE)**: Authenticate using Ethereum wallets
- **Traditional Auth**: Standard username/email/password authentication
- **JWT Tokens**: Secure API access with JSON Web Tokens
- **Permission Controls**: Different capabilities for different user types

Both types of users may post content, but only SIWE (wallet-authenticated) users can post bounties.

## API Endpoints

Key endpoints include:
- `/api/thread-list/`: List all discussion threads
- `/api/thread-posts/`: Get posts for a specific thread
- `/api/post/`, `/api/question/`, `/api/answer/`: Create content
- `/api/selection/`: Select the best answer
- `/api/confirm/`: Confirm on-chain status
- `/api/auth/`: Authentication endpoints

## Setup and Installation

### Install dependencies and set up your database

```bash
git clone https://github.com/matthew-ritch/facthound
cd facthound
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
```

### Environment Variables

Create a `.env` file with the following variables:
```
SECRET_KEY=your_django_secret_key
DEBUG=True
ALCHEMY_API_ENDPOINT=https://eth-mainnet.g.alchemy.com/v2
ALCHEMY_API_KEY=your_alchemy_api_key
BASE_MAINNET_FACTHOUND=facthound_contract_address
```

### Run Development Server

```bash
python manage.py runserver
```

### Run Tests
```bash
python manage.py test
```

## Blockchain Integration

Facthound integrates with the Ethereum blockchain using:

- **Web3.py**: For interacting with Ethereum nodes
- **FactHound Smart Contract**: An escrow contract for holding and distributing bounties
- **SIWE Authentication**: For verifying Ethereum wallet ownership

