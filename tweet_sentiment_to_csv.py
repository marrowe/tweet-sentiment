# -*- coding: utf-8 -*-

""" ------------------------------------------------------------------------------
tweet_sentiment_to_csv.py

	a simple Twitter streamer & sentiment analyzer for Python 3
	that downloads tweets & user info from search queries

	by Margaret Anne Rowe, with ample help from Ethan Beaman
		mar299					|				 ejb100
						@ georgetown.edu

	This script queries user-defined search terms using Tweepy StreamListener,
	then filters tweets for further keywords in the tweeter's Location and Description.
	It performs simple polarity and subjectivity analysis using TextBlob, then saves to CSV.
	Originally meant for perceptual dialectology research, it can be edited for various types of data-gathering.
	Can collect ~3200 items.

Written for LING-452, American Dialects
Prof. Natalie Schilling, Georgetown University, Fall 2018

	Last revised: January 2, 2019

Note: If you're using Python 3.7+ with Tweepy 3.7 or earlier, you'll need to go into the
	Tweepy source code and change all instances of "async" to "async_" or something similar,
	as async is now a reserved keyword.

------------------------------------------------------------------------------"""

from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import TweepError
from tweepy import API
from tweepy import Cursor

import csv
import re
import argparse
from textblob import TextBlob

# Allows for optional command line configuration of # of tweets and file destination.
parser = argparse.ArgumentParser()
parser.add_argument('-number', '-n', action="store", dest="n", type=int, default="1000")
parser.add_argument('-file', '-f', action="store", dest="f", type=str, default="your_tweets.csv")
parser = parser.parse_args()

# Search terms passed to Twitter. Use -filter:retweets to prevent duplicates.
my_queries = ['southern accent -filter:retweets', 'new york accent -filter:retweets',
			  'californian accent -filter:retweets']

# Used to extract specific metadata from larger tweets. All options:
	# created_at (str), id (int), id_str (str), full_text (str), truncated (bool), display_text_range (list),
	# entities (dict), metadata (dict), source (str),in_reply_to_status_id (int/None),
	# in_reply_to_status_id_str (str/None), in_reply_to_user_id (int/None), in_reply_to_user_id_str (str/None),
	# user (dict), geo (str/None), coordinates (int/None), place (str/None), contributors (str/None),
	# is_quote_status (bool), retweet_count (int), favorite_count (int), favorited (bool), retweeted (bool), lang (str)
metadata_fields = ['created_at', 'name', 'screen_name', 'location', 'description']

filter_terms = ['dc', 'DMV', 'georgetown', 'gtown', 'GU', '37th and O', '202']


class MyStreamListener(StreamListener):
	# Initializes the Tweepy StreamListener object used to fetch tweets from Twitter.

	def on_data(self, status):
		return True

	def on_error(self, status_code):
		if status_code == 420:
			print("wee woo wee woo, it didn't work! Disconnecting...")
			return False


def start_api():
	"""--------------------------------------------------------------------------
		Takes your individual developer tokens to connect to the Twitter API.
		
	:return: a successfully-initialized connection to Twitter
	--------------------------------------------------------------------------"""
	# Keys and tokens are unique access codes that vary for each person accessing Twitter's API.
	# You have to sign up for a developer account to get these - developer.twitter.com
	# (It's easy and free)
	api_key = ''
	api_secret_key = ''
	access_token = ''
	access_token_secret = ''

	auth = OAuthHandler(api_key, api_secret_key)  # This is where you hack the mainframe
	auth.set_access_token(access_token, access_token_secret)

	try:
		auth.get_authorization_url()
		print("You're in! API connected.")
	except TweepError:
		print("You're not in! API did not connect.")

	# Twitter limits the amount of tweets you can download at once, so Tweepy will wait it out.
	return API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)


def get_data(status):
	"""--------------------------------------------------------------------------
		Extracts datetime, @handle, display name, location, description, and tweet text
		from the user dict of individual tweet metadata.

	:param status: dict of metadata of one raw tweet
	:return: tuple of specified tweet metadata and text of tweet
	--------------------------------------------------------------------------"""
	user = status.get('user')  # user is a dictionary within status - contains metadata of tweeter
	data = {f: user.get(f) for f in metadata_fields}  # extracts metadata specified in constant
	data.update({'text': status.get('full_text')})  # extracts text of actual tweet
	return data.items()


def scraper(queries):
	"""--------------------------------------------------------------------------
		Collects tweets for analysis using a Tweepy cursor object and user-defined search terms.

	:param queries: list of searches to be run on Twitter
	:return: set of tweet tuples, each containing tuple metadata specified in get_data
	--------------------------------------------------------------------------"""
	# my_queries: List of search terms to look for. Follows standard Twitter syntax
	# -filter:retweets excludes all RTs - recommended for sentiment analysis
	api = start_api()  # Initializes API from class

	all_tweets = set()

	for search in queries:
		query = Cursor(api.search, rpp=100, tweet_mode='extended', q=search)
		results = query.items(parser.n)  # Gathers user-defined number of items. Defaults to 1000.
		# Using specifications in get_data(), saves desired metadata fields of an individual tweet.
		temp_list = list(map(get_data, [status._json for status in results]))
		for t in temp_list:  # Converts tweet metadata into tuples, then adds to set of all downloaded tweets
			all_tweets.add(tuple(t))

	return all_tweets


def filter(tweet_tup):
	"""--------------------------------------------------------------------------
		Filters tweets for user-defined words/phrases in individual tweet tuples. Meant to pare down
		results using criteria beyond the original search terms, e.g., user locations.
		Adds sentiment analysis of tweet text using TextBlob's sentiment() function.

	:param tweet_tup: set of tweet tuples that have already been filtered for desired metadata fields.
	:return: list of dictionaries of tweets that successfully matched the criteria in get_filter_data(),
		as well as their polarity and subjectiviy scores
	--------------------------------------------------------------------------"""
	saved_tweets = []

	for tweet in tweet_tup:
		# Performs sentiment analysis, then saves tweet to list of all matches
		if any(re.search(r'\b' + f + r'\b', tweet[3][1], re.I) for f in filter_terms) \
				or any(re.search(r'\b' + f + r'\b', tweet[4][1], re.I) for f in filter_terms):
			current_tweet = dict(tweet)
			current_tweet.update(sentiment_saver(current_tweet['text']))
			saved_tweets.append(current_tweet)

	return saved_tweets


def sentiment_saver(individual_tweet):
	"""
		Performs sentiment analysis on the text of an individual tweet using TextBlob.

	:param individual_tweet: string of tweet text
	:return: dictionary of polarity and subjectivity scores for individual_tweet
	"""
	sentiment_obj = TextBlob(individual_tweet)
	return {"polarity": sentiment_obj.sentiment.polarity, "subjectivity": sentiment_obj.sentiment.subjectivity}


def write_to_csv(final_tweets):
	"""
		Saves gathered tweet data in csv format.

	:param final_tweets: dictionary of tweets to be saved in csv format
	:return: None
	"""
	with open(parser.f, 'w', encoding='utf-8') as csvfile:
		fieldnames = metadata_fields + ['text', 'polarity', 'subjectivity']
		writer = csv.DictWriter(csvfile, fieldnames=fieldnames, lineterminator='\n')
		writer.writeheader()
		writer.writerows(final_tweets)
		print("All done! Your tweets have been saved to " + parser.f)

	return None


def main():
	tweets = scraper(my_queries)
	filtered_tweets = filter(tweets)
	write_to_csv(filtered_tweets)
	return None


if __name__ == '__main__':
	main()
