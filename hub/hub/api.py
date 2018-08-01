# Copyright (c) 2015, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe import _
from frappe.utils import random_string

from curation import (get_item_fields, post_process_item_details, get_items_by_country,
	get_items_with_images, get_random_items_from_each_hub_seller)

from log import update_hub_seller_activity, update_hub_item_view_log

@frappe.whitelist(allow_guest=True)
def register(profile):
	"""Register on the hub."""
	try:
		profile = frappe._dict(json.loads(profile))

		password = random_string(16)
		email = profile.company_email
		company_name = profile.company

		if frappe.db.exists('User', email):
			user = frappe.get_doc('User', email)
			user.enabled = 1
			user.new_password = password
			user.save(ignore_permissions=True)
		else:
			# register
			user = frappe.get_doc({
				'doctype': 'User',
				'email': email,
				'first_name': company_name,
				'new_password': password
			})

			user.append_roles("System Manager")
			user.flags.delay_emails = True
			user.insert(ignore_permissions=True)

			seller_data = profile.update({
				'enabled': 1,
				'doctype': 'Hub Seller',
				'user': email,
				'hub_seller_activity':[{'type': 'Created'}]
			})
			seller = frappe.get_doc(seller_data)
			seller.insert(ignore_permissions=True)


		return {
			'email': email,
			'password': password
		}

	except Exception as e:
		print("Hub Server Exception")
		print(frappe.get_traceback())

		frappe.throw(frappe.get_traceback())

		# return {
		# 	'error': "Hub Server Exception",
		# 	'traceback': frappe.get_traceback()
		# }

@frappe.whitelist(allow_guest=True)
def get_data_for_homepage(country=None):
	'''
	Get curated item list for the homepage.
	'''
	fields = get_item_fields()
	items = []

	items_by_country = []
	if country:
		items_by_country += get_items_by_country(country)

	items_with_images = get_items_with_images()

	return dict(
		items_by_country = items_by_country,
		items_with_images = items_with_images or [],
		random_items = get_random_items_from_each_hub_seller() or []
	)

@frappe.whitelist()
def get_items(keyword=None, hub_seller=None):
	'''
	Get items by matching it with the keywords field
	'''
	fields = get_item_fields()

	filters = {
		'keywords': ['like', '%' + keyword + '%']
	}

	if hub_seller:
		filters["hub_seller"] = hub_seller

	items = frappe.get_all('Hub Item', fields=fields,
		filters=filters)

	items = post_process_item_details(items)

	return items

@frappe.whitelist()
def add_hub_seller_activity(hub_seller, activity_details):
	return update_hub_seller_activity(hub_seller, activity_details)

@frappe.whitelist()
def get_hub_seller_profile(hub_seller):
	profile = frappe.get_doc("Hub Seller", hub_seller).as_dict()

	for log in profile.hub_seller_activity:
		log.pretty_date = frappe.utils.pretty_date(log.get('creation'))

	return profile

@frappe.whitelist(allow_guest=True)
def get_item_details(hub_seller, hub_item_code):
	fields = get_item_fields()
	items = frappe.get_all('Hub Item', fields=fields, filters={ 'name': hub_item_code })
	items = post_process_item_details(items)
	update_hub_item_view_log(hub_seller, hub_item_code)
	return items[0]

@frappe.whitelist()
def get_item_reviews(hub_item_code):
	reviews = frappe.db.get_all('Hub Item Review', fields=['*'],
		filters={
			'parenttype': 'Hub Item',
			'parentfield': 'reviews',
			'parent': hub_item_code
		}, order_by='modified desc')

	return reviews or []

@frappe.whitelist()
def add_item_review(hub_item_code, review):
	'''Adds a review record for Hub Item and limits to 1 per user'''
	new_review = json.loads(review)

	item_doc = frappe.get_doc('Hub Item', hub_item_code)
	existing_reviews = item_doc.get('reviews')

	# dont allow more than 1 review
	for review in existing_reviews:
		if review.get('user') == new_review.get('user'):
			return dict(error='Cannot add more than 1 review for the user {0}'.format(new_review.get('user')))

	item_doc.append('reviews', new_review)
	item_doc.save()

	return item_doc.get('reviews')[-1]

@frappe.whitelist()
def get_categories(parent='All Categories'):
	# get categories info with parent category and stuff
	categories = frappe.get_all('Hub Category',
		filters={'parent_hub_category': parent},
		fields=['name'],
		order_by='name asc')

	return categories

@frappe.whitelist()
def get_item_favourites():
	return []
