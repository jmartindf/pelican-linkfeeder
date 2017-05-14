#!/usr/bin/env python
# encoding: utf-8

"""
Link Feed Generator for Pelican.
"""

from __future__ import unicode_literals


import six
from jinja2 import Markup
from pelican import signals
from pelican.writers import Writer
from pelican.generators import Generator
from pelican.utils import set_date_tzinfo
from feedgenerator import Rss201rev2Feed, Atom1Feed, get_tag_uri
from feedgenerator.django.utils.feedgenerator import rfc2822_date

class RssPuSHFeed(Rss201rev2Feed):
	"""Helper class which generates the XML based in the global settings"""
	def __init__(self, *args, **kwargs):
		"""Nice method docstring goes here"""
		super(RssPuSHFeed, self).__init__(*args, **kwargs)

	def set_settings(self, settings):
		"""Helper function which just receives the podcast settings.
		:param settings: A dictionary with all the site settings.
		"""
		self.settings = settings

	def add_root_elements(self, handler):
		super(RssPuSHFeed,self).add_root_elements(handler)
		if 'WEBSUB_HUB' in self.settings and self.settings['WEBSUB_HUB'] != "":
			handler.addQuickElement("link", None,
					{"rel": "self", "href": self.feed['feed_url'],"xmlns": "http://www.w3.org/2005/Atom"})
			handler.addQuickElement("link", None,
					{"rel": "hub", "href": self.settings['WEBSUB_HUB'],"xmlns": "http://www.w3.org/2005/Atom"})

class Atom1PuSHFeed(Atom1Feed):
	"""Helper class which generates the XML based in the global settings"""
	def __init__(self, *args, **kwargs):
		"""Nice method docstring goes here"""
		super(Atom1PuSHFeed, self).__init__(*args, **kwargs)

	def set_settings(self, settings):
		"""Helper function which just receives the podcast settings.
		:param settings: A dictionary with all the site settings.
		"""
		self.settings = settings

	def add_root_elements(self, handler):
		super(Atom1PuSHFeed,self).add_root_elements(handler)
		if 'WEBSUB_HUB' in self.settings and self.settings['WEBSUB_HUB'] != "":
			handler.addQuickElement("link", None,
					{"rel": "hub", "href": self.settings['WEBSUB_HUB']})


class LinkFeedWriter(Writer):
	"""Writer class for our link feed.  This class is responsible for
	invoking the RssPuSHFeed or Atom1PuSHFeed and writing the feed itself
	(using it's superclass methods)."""

	def __init__(self, *args, **kwargs):
		"""Class initializer"""
		super(LinkFeedWriter, self).__init__(*args, **kwargs)

	def _create_new_feed(self, *args):
		"""Helper function (called by the super class) which will initialize
		the Feed object."""
		if len(args) == 2:
			# we are on pelican <2.7
			feed_type, context = args
		elif len(args) == 3:
			# we are on Pelican >=2.7
			feed_type, feed_title, context = args
		else:
			# this is not expected, let's provide a useful message
			raise Exception(
				'The Writer._create_new_feed signature has changed, check the '
				'current Pelican source for the updated signature'
			)
		feed_class = RssPuSHFeed if feed_type == 'rss' else Atom1PuSHFeed

		sitename = Markup(context['SITENAME']).striptags()
		feed = feed_class(
			title=sitename,
			link=(self.site_url + '/'),
			feed_url=self.feed_url,
			description=context.get('SITESUBTITLE', ''))
		feed.set_settings(self.settings)
		return feed

	def _add_item_to_the_feed(self, feed, item):
		"""Performs an 'in-place' update of existing 'published' articles
		in ``feed`` by creating a new entry using the contents from the
		``item`` being passed.
		This method is invoked by pelican's core.

		:param feed: A Feed instance.
		:param item: An article (pelican's Article object).

		"""
		title = Markup(item.title).striptags()
		link = '%s/%s' % (self.site_url, item.url)
		appendContent = ""
		appendTitle = ""

		if hasattr(item,"link"):
			appendContent = '<p><a href="%s">%s</a></p>' % (link, self.settings.get('LINK_BLOG_PERMALINK_GLYPH','&infin;'))
			appendTitle = self.settings.get('LINK_BLOG_APPEND_TITLE','')
			link = item.link

		feed.add_item(
			title=title + appendTitle,
			link=link,
			unique_id=get_tag_uri(link, item.date),
			description=item.get_content(self.site_url) + appendContent,
			categories=item.tags if hasattr(item, 'tags') else None,
			author_name=getattr(item, 'author', ''),
			pubdate=set_date_tzinfo(
				item.modified if hasattr(item, 'modified') else item.date,
				self.settings.get('TIMEZONE', None)
			)
		)

class LinkFeedGenerator(Generator):
	"""Generates content by inspecting all articles and invokes the
	LinkFeedWriter object, which will write the Link Feed."""

	def __init__(self, *args, **kwargs):
		"""Starts a brand new feed generator."""
		super(LinkFeedGenerator, self).__init__(*args, **kwargs)
		# Initialize the number of posts and where to save the feed.
		self.posts = []

	def generate_context(self):
		"""Looks for all 'published' articles and add them to the posts
		list."""
		for article in self.context['articles']:
			if (article.status.lower()) == "published":
				self.posts.append(article)

	def generate_output(self, writer):
		"""Write out the link feed to a file.

		:param writer: A ``Pelican Writer`` instance.
		"""
		writer = LinkFeedWriter(self.output_path, self.settings)
		if self.settings.get('LINK_FEED_RSS'):
			writer.write_feed(self.posts, self.context, self.settings.get('LINK_FEED_RSS'), feed_type="rss")
		if self.settings.get('LINK_FEED_ATOM'):
			writer.write_feed(self.posts, self.context, self.settings.get('LINK_FEED_ATOM'))

def get_generators(generators):
	"""Module function invoked by the signal 'get_generators'."""
	return LinkFeedGenerator


def register():
	"""Registers the module function `get_generators`."""
	signals.get_generators.connect(get_generators)
