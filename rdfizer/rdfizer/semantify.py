import os
import re
import csv
import sys
import uuid
import rdflib
import getopt
import subprocess
from rdflib.plugins.sparql import prepareQuery
from configparser import ConfigParser, ExtendedInterpolation
from rdfizer.triples_map import TriplesMap as tm
import traceback
from mysql import connector
from concurrent.futures import ThreadPoolExecutor
import time
import json
import xml.etree.ElementTree as ET
import psycopg2

from .functions import *

try:
	from triples_map import TriplesMap as tm
except:
	from .triples_map import TriplesMap as tm	

# Work in the rr:sqlQuery (change mapping parser query, add sqlite3 support, etc)
# Work in the "when subject is empty" thing (uuid.uuid4(), dependency graph over the ) 

global g_triples 
g_triples = {}
global number_triple
number_triple = 0
global triples
triples = []
global duplicate
duplicate = ""
global start_time
start_time = 0
global user, password, port, host
user, password, port, host = "", "", "", ""
global join_table 
join_table = {}
global po_table
po_table = {}
global enrichment
enrichment = ""

def hash_maker(parent_data, parent_subject, child_object):
	hash_table = {}
	for row in parent_data:
		if child_object.parent[0] in row.keys():
			if row[child_object.parent[0]] in hash_table:
				if duplicate == "yes":
					if parent_subject.subject_map.subject_mapping_type == "reference":
						value = string_substitution(parent_subject.subject_map.value, ".+", row, "object")
						if value is not None:
							if "http" in value and "<" not in value:
								value = "<" + value[1:-1] + ">"
							elif "http" in value and "<" in value:
								value = value[1:-1] 
						if value not in hash_table[row[child_object.parent[0]]]:
							hash_table[row[child_object.parent[0]]].append(value)
					else:
						if "<" + string_substitution(parent_subject.subject_map.value, "{(.+?)}", row, "object") + ">" not in hash_table[row[child_object.parent[0]]]:
							hash_table[row[child_object.parent[0]]].append("<" + string_substitution(parent_subject.subject_map.value, "{(.+?)}", row, "object") + ">") 
				else:
					if parent_subject.subject_map.subject_mapping_type == "reference":
						value = string_substitution(parent_subject.subject_map.value, ".+", row, "object")
						if "http" in value and "<" not in value:
							value = "<" + value[1:-1] + ">"
						elif "http" in value and "<" in value:
							value = value[1:-1] 
						hash_table[row[child_object.parent[0]]].append(value)
					else:
						hash_table[row[child_object.parent[0]]].append("<" + string_substitution(parent_subject.subject_map.value, "{(.+?)}", row, "object") + ">")

			else:
				if parent_subject.subject_map.subject_mapping_type == "reference":
					value = string_substitution(parent_subject.subject_map.value, ".+", row, "object")
					if value is not None:
						if "http" in value and "<" not in value:
							value = "<" + value[1:-1] + ">"
						elif "http" in value and "<" in value:
							value = value[1:-1] 
					hash_table.update({row[child_object.parent[0]] : [value]}) 
				else:	
					hash_table.update({row[child_object.parent[0]] : ["<" + string_substitution(parent_subject.subject_map.value, "{(.+?)}", row, "object") + ">"]})
	join_table.update({parent_subject.triples_map_id + "_" + child_object.child[0] : hash_table})

def hash_maker_list(parent_data, parent_subject, child_object):
	hash_table = {}
	for row in parent_data:
		if sublist(child_object.parent,row.keys()):
			if child_list_value(child_object.parent,row) in hash_table:
				if duplicate == "yes":
					if parent_subject.subject_map.subject_mapping_type == "reference":
						value = string_substitution(parent_subject.subject_map.value, ".+", row, "object")
						if value is not None:
							if "http" in value and "<" not in value:
								value = "<" + value[1:-1] + ">"
							elif "http" in value and "<" in value:
								value = value[1:-1] 
						if value not in hash_table[row[child_object.parent]]:
							hash_table[child_list_value(child_object.parent,row)].append(value)
					else:
						if "<" + string_substitution(parent_subject.subject_map.value, "{(.+?)}", row, "object") + ">" not in hash_table[row[child_object.parent]]:
							hash_table[child_list_value(child_object.parent,row)].append("<" + string_substitution(parent_subject.subject_map.value, "{(.+?)}", row, "object") + ">") 
				else:
					if parent_subject.subject_map.subject_mapping_type == "reference":
						value = string_substitution(parent_subject.subject_map.value, ".+", row, "object")
						if "http" in value and "<" not in value:
							value = "<" + value[1:-1] + ">"
						elif "http" in value and "<" in value:
							value = value[1:-1] 
						hash_table[child_list_value(child_object.parent,row)].append(value)
					else:
						hash_table[child_list_value(child_object.parent,row)].append("<" + string_substitution(parent_subject.subject_map.value, "{(.+?)}", row, "object") + ">")

			else:
				if parent_subject.subject_map.subject_mapping_type == "reference":
					value = string_substitution(parent_subject.subject_map.value, ".+", row, "object")
					if value is not None:
						if "http" in value and "<" not in value:
							value = "<" + value[1:-1] + ">"
						elif "http" in value and "<" in value:
							value = value[1:-1] 
					hash_table.update({child_list_value(child_object.parent,row) : [value]}) 
				else:	
					hash_table.update({child_list_value(child_object.parent,row) : ["<" + string_substitution(parent_subject.subject_map.value, "{(.+?)}", row, "object") + ">"]})
	join_table.update({parent_subject.triples_map_id + "_" + child_list(child_object.child) : hash_table})

def hash_maker_xml(parent_data, parent_subject, child_object):
	hash_table = {}
	for row in parent_data:
		if row.find(child_object.parent[0]).text in hash_table:
			if duplicate == "yes":
				if parent_subject.subject_map.subject_mapping_type == "reference":
					value = string_substitution_xml(parent_subject.subject_map.value, ".+", row, "object")
					if value is not None:
						if "http" in value:
							value = "<" + value[1:-1] + ">"
					if value not in hash_table[row.find(child_object.parent[0]).text]:
						hash_table[row.find(child_object.parent[0]).text].append(value)
				else:
					if "<" + string_substitution_xml(parent_subject.subject_map.value, "{(.+?)}", row, "object") + ">" not in hash_table[row.find(child_object.parent[0]).text]:
						hash_table[row.find(child_object.parent[0]).text].append("<" + string_substitution(parent_subject.subject_map.value, "{(.+?)}", row, "object") + ">")
			else:
				if parent_subject.subject_map.subject_mapping_type == "reference":
					value = string_substitution_xml(parent_subject.subject_map.value, ".+", row, "object")
					if value is not None:
						if "http" in value:
							value = "<" + value[1:-1] + ">"
					hash_table[row.find(child_object.parent[0]).text].append(value)
				else:
					hash_table[row.find(child_object.parent[0]).text].append("<" + string_substitution_xml(parent_subject.subject_map.value, "{(.+?)}", row, "object") + ">")

		else:
			if parent_subject.subject_map.subject_mapping_type == "reference":
				value = string_substitution(parent_subject.subject_map.value, ".+", row, "object")
				if value is not None:
					if "http" in value:
						value = "<" + value[1:-1] + ">"
				hash_table.update({row.find(child_object.parent[0]).text : [value]}) 
			else:	
				hash_table.update({row.find(child_object.parent[0]).text : ["<" + string_substitution_xml(parent_subject.subject_map.value, "{(.+?)}", row, "object") + ">"]}) 
	join_table.update({parent_subject.triples_map_id + "_" + child_object.child[0] : hash_table})


def hash_maker_array(parent_data, parent_subject, child_object, mapping_type):
	hash_table = {}
	row_headers=[x[0] for x in parent_data.description]
	for row in parent_data:
		element =row[row_headers.index(child_object.parent[0])]
		if type(element) is int:
			element = str(element)
		if row[row_headers.index(child_object.parent[0])] in hash_table:
			if duplicate == "yes":
				if "<" + string_substitution_array(parent_subject.subject_map.value, "{(.+?)}", row, row_headers,"object") + ">" not in hash_table[row[child_object.parent[0]]]:
					hash_table[element].append("<" + string_substitution_array(parent_subject.subject_map.value, "{(.+?)}", row, row_headers,"object") + ">")
			else:
				hash_table[element].append("<" + string_substitution_array(parent_subject.subject_map.value, "{(.+?)}", row, row_headers, "object") + ">")
			
		else:
			hash_table.update({element : ["<" + string_substitution_array(parent_subject.subject_map.value, "{(.+?)}", row, row_headers, "object") + ">"]}) 
	join_table.update({parent_subject.triples_map_id + "_" + child_object.child[0]  : hash_table})


def mapping_parser(mapping_file):

	"""
	(Private function, not accessible from outside this package)

	Takes a mapping file in Turtle (.ttl) or Notation3 (.n3) format and parses it into a list of
	TriplesMap objects (refer to TriplesMap.py file)

	Parameters
	----------
	mapping_file : string
		Path to the mapping file

	Returns
	-------
	A list of TriplesMap objects containing all the parsed rules from the original mapping file
	"""

	mapping_graph = rdflib.Graph()

	try:
		mapping_graph.load(mapping_file, format='n3')
	except Exception as n3_mapping_parse_exception:
		print(n3_mapping_parse_exception)
		print('Could not parse {} as a mapping file'.format(mapping_file))
		print('Aborting...')
		sys.exit(1)

	mapping_query = """
		prefix rr: <http://www.w3.org/ns/r2rml#> 
		prefix rml: <http://semweb.mmlab.be/ns/rml#> 
		prefix ql: <http://semweb.mmlab.be/ns/ql#> 
		prefix d2rq: <http://www.wiwiss.fu-berlin.de/suhl/bizer/D2RQ/0.1#> 
		SELECT DISTINCT *
		WHERE {

	# Subject -------------------------------------------------------------------------
			?triples_map_id rml:logicalSource ?_source .
			OPTIONAL{?_source rml:source ?data_source .}
			OPTIONAL {?_source rml:referenceFormulation ?ref_form .}
			OPTIONAL { ?_source rml:iterator ?iterator . }
			OPTIONAL { ?_source rr:tableName ?tablename .}
			OPTIONAL { ?_source rml:query ?query .}
			
			?triples_map_id rr:subjectMap ?_subject_map .
			OPTIONAL {?_subject_map rr:template ?subject_template .}
			OPTIONAL {?_subject_map rml:reference ?subject_reference .}
			OPTIONAL {?_subject_map rr:constant ?subject_constant}
			OPTIONAL { ?_subject_map rr:class ?rdf_class . }
			OPTIONAL { ?_subject_map rr:termType ?termtype . }
			OPTIONAL { ?_subject_map rr:graph ?graph . }
			OPTIONAL { ?_subject_map rr:graphMap ?_graph_structure .
					   ?_graph_structure rr:constant ?graph . }
			OPTIONAL { ?_subject_map rr:graphMap ?_graph_structure .
					   ?_graph_structure rr:template ?graph . }		   

	# Predicate -----------------------------------------------------------------------
			OPTIONAL {
			?triples_map_id rr:predicateObjectMap ?_predicate_object_map .
			
			OPTIONAL {
				?triples_map_id rr:predicateObjectMap ?_predicate_object_map .
				?_predicate_object_map rr:predicateMap ?_predicate_map .
				?_predicate_map rr:constant ?predicate_constant .
			}
			OPTIONAL {
				?_predicate_object_map rr:predicateMap ?_predicate_map .
				?_predicate_map rr:template ?predicate_template .
			}
			OPTIONAL {
				?_predicate_object_map rr:predicateMap ?_predicate_map .
				?_predicate_map rml:reference ?predicate_reference .
			}
			OPTIONAL {
				?_predicate_object_map rr:predicate ?predicate_constant_shortcut .
			 }
			

	# Object --------------------------------------------------------------------------
			OPTIONAL {
				?_predicate_object_map rr:objectMap ?_object_map .
				?_object_map rr:constant ?object_constant .
				OPTIONAL {
					?_object_map rr:datatype ?object_datatype .
				}
			}
			OPTIONAL {
				?_predicate_object_map rr:objectMap ?_object_map .
				?_object_map rr:template ?object_template .
				OPTIONAL {?_object_map rr:termType ?term .}
				OPTIONAL {
					?_object_map rr:datatype ?object_datatype .
				}
			}
			OPTIONAL {
				?_predicate_object_map rr:objectMap ?_object_map .
				?_object_map rml:reference ?object_reference .
				OPTIONAL { ?_object_map rr:language ?language .}
				OPTIONAL {?_object_map rr:termType ?term .}
				OPTIONAL {
					?_object_map rr:datatype ?object_datatype .
				}
			}
			OPTIONAL {
				?_predicate_object_map rr:objectMap ?_object_map .
				?_object_map rr:parentTriplesMap ?object_parent_triples_map .
				OPTIONAL {
					?_object_map rr:joinCondition ?join_condition .
					?join_condition rr:child ?child_value;
								 rr:parent ?parent_value.
					OPTIONAL {?_object_map rr:termType ?term .}
				}
			}
			OPTIONAL {
				?_predicate_object_map rr:object ?object_constant_shortcut .
				OPTIONAL {
					?_object_map rr:datatype ?object_datatype .
				}
			}
			}
			OPTIONAL {
				?_source a d2rq:Database;
  				d2rq:jdbcDSN ?jdbcDSN; 
  				d2rq:jdbcDriver ?jdbcDriver; 
			    d2rq:username ?user;
			    d2rq:password ?password .
			}
		} """

	mapping_query_results = mapping_graph.query(mapping_query)
	triples_map_list = []


	for result_triples_map in mapping_query_results:
		triples_map_exists = False
		for triples_map in triples_map_list:
			triples_map_exists = triples_map_exists or (str(triples_map.triples_map_id) == str(result_triples_map.triples_map_id))
		
		if not triples_map_exists:
			if result_triples_map.subject_template is not None:
				if result_triples_map.rdf_class is None:
					reference, condition = string_separetion(str(result_triples_map.subject_template))
					subject_map = tm.SubjectMap(str(result_triples_map.subject_template), condition, "template", result_triples_map.rdf_class, result_triples_map.termtype, result_triples_map.graph)
				else:
					reference, condition = string_separetion(str(result_triples_map.subject_template))
					subject_map = tm.SubjectMap(str(result_triples_map.subject_template), condition, "template", str(result_triples_map.rdf_class), result_triples_map.termtype, result_triples_map.graph)
			elif result_triples_map.subject_reference is not None:
				if result_triples_map.rdf_class is None:
					reference, condition = string_separetion(str(result_triples_map.subject_reference))
					subject_map = tm.SubjectMap(str(result_triples_map.subject_reference), condition, "reference", result_triples_map.rdf_class, result_triples_map.termtype, result_triples_map.graph)
				else:
					reference, condition = string_separetion(str(result_triples_map.subject_reference))
					subject_map = tm.SubjectMap(str(result_triples_map.subject_reference), condition, "reference", str(result_triples_map.rdf_class), result_triples_map.termtype, result_triples_map.graph)
			elif result_triples_map.subject_constant is not None:
				if result_triples_map.rdf_class is None:
					reference, condition = string_separetion(str(result_triples_map.subject_constant))
					subject_map = tm.SubjectMap(str(result_triples_map.subject_constant), condition, "constant", result_triples_map.rdf_class, result_triples_map.termtype, result_triples_map.graph)
				else:
					reference, condition = string_separetion(str(result_triples_map.subject_constant))
					subject_map = tm.SubjectMap(str(result_triples_map.subject_constant), condition, "constant", str(result_triples_map.rdf_class), result_triples_map.termtype, result_triples_map.graph)
				
			mapping_query_prepared = prepareQuery(mapping_query)


			mapping_query_prepared_results = mapping_graph.query(mapping_query_prepared, initBindings={'triples_map_id': result_triples_map.triples_map_id})

			join_predicate = {}
			predicate_object_maps_list = []

			for result_predicate_object_map in mapping_query_prepared_results:
				join = True
				if result_predicate_object_map.predicate_constant is not None:
					predicate_map = tm.PredicateMap("constant", str(result_predicate_object_map.predicate_constant), "")
				elif result_predicate_object_map.predicate_constant_shortcut is not None:
					predicate_map = tm.PredicateMap("constant shortcut", str(result_predicate_object_map.predicate_constant_shortcut), "")
				elif result_predicate_object_map.predicate_template is not None:
					template, condition = string_separetion(str(result_predicate_object_map.predicate_template))
					predicate_map = tm.PredicateMap("template", template, condition)
				elif result_predicate_object_map.predicate_reference is not None:
					reference, condition = string_separetion(str(result_predicate_object_map.predicate_reference))
					predicate_map = tm.PredicateMap("reference", reference, condition)
				else:
					predicate_map = tm.PredicateMap("None", "None", "None")

				if result_predicate_object_map.object_constant is not None:
					object_map = tm.ObjectMap("constant", str(result_predicate_object_map.object_constant), str(result_predicate_object_map.object_datatype), "None", "None", result_predicate_object_map.term, result_predicate_object_map.language)
				elif result_predicate_object_map.object_template is not None:
					object_map = tm.ObjectMap("template", str(result_predicate_object_map.object_template), str(result_predicate_object_map.object_datatype), "None", "None", result_predicate_object_map.term, result_predicate_object_map.language)
				elif result_predicate_object_map.object_reference is not None:
					object_map = tm.ObjectMap("reference", str(result_predicate_object_map.object_reference), str(result_predicate_object_map.object_datatype), "None", "None", result_predicate_object_map.term, result_predicate_object_map.language)
				elif result_predicate_object_map.object_parent_triples_map is not None:
					if predicate_map.value not in join_predicate:
						join_predicate[predicate_map.value] = {"predicate":predicate_map, "childs":[str(result_predicate_object_map.child_value)], "parents":[str(result_predicate_object_map.parent_value)], "triples_map":str(result_predicate_object_map.object_parent_triples_map)}
					else:
						join_predicate[predicate_map.value]["childs"].append(str(result_predicate_object_map.child_value))
						join_predicate[predicate_map.value]["parents"].append(str(result_predicate_object_map.parent_value))
					join = False
				elif result_predicate_object_map.object_constant_shortcut is not None:
					object_map = tm.ObjectMap("constant shortcut", str(result_predicate_object_map.object_constant_shortcut), str(result_predicate_object_map.object_datatype), "None", "None", result_predicate_object_map.term, result_predicate_object_map.language)
				else:
					object_map = tm.ObjectMap("None", "None", "None", "None", "None", "None", "None")

				if join:
					predicate_object_maps_list += [tm.PredicateObjectMap(predicate_map, object_map)]
				join = True

			if join_predicate:
				for jp in join_predicate.keys():
					object_map = tm.ObjectMap("parent triples map", join_predicate[jp]["triples_map"], str(result_predicate_object_map.object_datatype), join_predicate[jp]["childs"], join_predicate[jp]["parents"],result_predicate_object_map.term, result_predicate_object_map.language)
					predicate_object_maps_list += [tm.PredicateObjectMap(join_predicate[jp]["predicate"], object_map)]

			current_triples_map = tm.TriplesMap(str(result_triples_map.triples_map_id), str(result_triples_map.data_source), subject_map, predicate_object_maps_list, ref_form=str(result_triples_map.ref_form), iterator=str(result_triples_map.iterator), tablename=str(result_triples_map.tablename), query=str(result_triples_map.query))
			triples_map_list += [current_triples_map]

	return triples_map_list


def semantify_xml(triples_map, triples_map_list, output_file_descriptor, csv_file, dataset_name):
	i = 0
	triples_map_triples = {}
	generated_triples = {}
	object_list = []

	with open(str(triples_map.data_source), "r") as input_file_descriptor:
		tree = ET.parse(input_file_descriptor)
		root = tree.getroot()

		for child in root:
			subject_value = string_substitution_xml(triples_map.subject_map.value, "{(.+?)}", child, "subject")

			if duplicate == "yes":
				triple_entry = {subject_value: [dictionary_maker_xml(child)]}	
				if subject_value in triples_map_triples:
					if dictionary_maker_xml(child) in triples_map_triples[subject_value]:
						subject = None
					else:
						if triples_map.subject_map.subject_mapping_type == "template":
							if triples_map.subject_map.term_type is None:
								if triples_map.subject_map.condition == "":

									try:
										subject = "<" + subject_value + ">"
										triples_map_triples[subject_value].append(dictionary_maker_xml(child)) 
									except:
										subject = None

								else:
								#	field, condition = condition_separetor(triples_map.subject_map.condition)
								#	if row[field] == condition:
									try:
										subject = "<" + subject_value  + ">"
										triples_map_triples[subject_value].append(dictionary_maker_xml(child)) 
									except:
										subject = None 
							else:
								if "IRI" in triples_map.subject_map.term_type:
									if triples_map.subject_map.condition == "":

										try:
											subject = "<http://example.com/base/" + subject_value + ">"
											triples_map_triples[subject_value].append(dictionary_maker_xml(child)) 
										except:
											subject = None

									else:
									#	field, condition = condition_separetor(triples_map.subject_map.condition)
									#	if row[field] == condition:
										try:
											subject = "<http://example.com/base/" + subject_value + ">"
											triples_map_triples[subject_value].append(dictionary_maker_xml(child)) 
										except:
											subject = None 

								elif "BlankNode" in triples_map.subject_map.term_type:
									if triples_map.subject_map.condition == "":

										try:
											subject = "_:" + subject_value
											triples_map_triples[subject_value].append(dictionary_maker_xml(child)) 
										except:
											subject = None

									else:
									#	field, condition = condition_separetor(triples_map.subject_map.condition)
									#	if row[field] == condition:
										try:
											subject = "_:" + subject_value  
											triples_map_triples[subject_value].append(dictionary_maker_xml(child)) 
										except:
											subject = None
											
								else:
									if triples_map.subject_map.condition == "":

										try:
											subject = "<" + subject_value + ">"
											triples_map_triples.update(triple_entry) 
										except:
											subject = None

									else:
									#	field, condition = condition_separetor(triples_map.subject_map.condition)
									#	if row[field] == condition:
										try:
											subject = "<" + subject_value + ">"
											triples_map_triples.update(triple_entry) 
										except:
											subject = None 
						elif "reference" in triples_map.subject_map.subject_mapping_type:
							subject_value = string_substitution_xml(triples_map.subject_map.value, ".+", child, "subject")
							if subject_value is not None:
								subject_value = subject_value[1:-1]
								if "/" in subject_value:
									i = len(subject_value) - 1
									temp = ""
									while  0 < i:
										if subject_value[i] == "/":
											break
										else:
											temp = subject_value[i] + temp
										i -= 1
									subject_value = temp
								if triples_map.subject_map.condition == "":

									try:
										subject = "<http://example.com/base/" + subject_value + ">"
										triples_map_triples.update(triple_entry) 
									except:
										subject = None

							else:
							#	field, condition = condition_separetor(triples_map.subject_map.condition)
							#	if row[field] == condition:
								try:
									subject = "<http://example.com/base/" + subject_value + ">"
									triples_map_triples.update(triple_entry) 
								except:
									subject = None

						elif "constant" in triples_map.subject_map.subject_mapping_type:
							subject = "<" + subject_value + ">"

						else:
							if triples_map.subject_map.condition == "":

								try:
									subject = "\"" + triples_map.subject_map.value + "\""
									triple_entry = {subject: [dictionary_maker_xml(child)]}	
									triples_map_triples.update(triple_entry) 
								except:
									subject = None

							else:
							#	field, condition = condition_separetor(triples_map.subject_map.condition)
							#	if row[field] == condition:
								try:
									subject = "\"" + triples_map.subject_map.value + "\""
									triple_entry = {subject: [dictionary_maker_xml(child)]}
									triples_map_triples.update(triple_entry) 
								except:
									subject = None
				else:
					if triples_map.subject_map.subject_mapping_type == "template":
						if triples_map.subject_map.term_type is None:
							if triples_map.subject_map.condition == "":

								try:
									subject = "<" + subject_value + ">"
									triples_map_triples.update(triple_entry) 
								except:
									subject = None

							else:
							#	field, condition = condition_separetor(triples_map.subject_map.condition)
							#	if row[field] == condition:
								try:
									subject = "<" + subject_value  + ">"
									triples_map_triples.update(triple_entry) 
								except:
									subject = None
						else:
							if "IRI" in triples_map.subject_map.term_type:
								if triples_map.subject_map.condition == "":

									try:
										subject = "<http://example.com/base/" + subject_value + ">"
										triples_map_triples.update(triple_entry) 
									except:
										subject = None

								else:
								#	field, condition = condition_separetor(triples_map.subject_map.condition)
								#	if row[field] == condition:
									try:
										subject = "<http://example.com/base/" + subject_value + ">"
										triples_map_triples.update(triple_entry) 
									except:
										subject = None
								
							elif "BlankNode" in triples_map.subject_map.term_type:
								if triples_map.subject_map.condition == "":

									try:
										subject = "_:" + subject_value 
										triples_map_triples.update(triple_entry) 
									except:
										subject = None

								else:
								#	field, condition = condition_separetor(triples_map.subject_map.condition)
								#	if row[field] == condition:
									try:
										subject = "_:" + subject_value 
										triples_map_triples.update(triple_entry) 
									except:
										subject = None
							else:
								if triples_map.subject_map.condition == "":

									try:
										subject = "<" + subject_value + ">"
										triples_map_triples.update(triple_entry) 
									except:
										subject = None

								else:
								#	field, condition = condition_separetor(triples_map.subject_map.condition)
								#	if row[field] == condition:
									try:
										subject = "<" + subject_value + ">"
										triples_map_triples.update(triple_entry) 
									except:
										subject = None

					elif "reference" in triples_map.subject_map.subject_mapping_type:
						if triples_map.subject_map.condition == "":
							subject_value = string_substitution_xml(triples_map.subject_map.value, ".+", child, "subject")
							subject_value = subject_value[1:-1]
							if "/" in subject_value:
								i = len(subject_value) - 1
								temp = ""
								while  0 < i:
									if subject_value[i] == "/":
										break
									else:
										temp = subject_value[i] + temp 
									i -= 1
								subject_value = temp
							try:
								subject = "<http://example.com/base/" + subject_value + ">"
								triples_map_triples.update(triple_entry) 
							except:
								subject = None

						else:
						#	field, condition = condition_separetor(triples_map.subject_map.condition)
						#	if row[field] == condition:
							try:
								subject = "<http://example.com/base/" + subject_value + ">"
								triples_map_triples.update(triple_entry) 
							except:
								subject = None

					elif "constant" in triples_map.subject_map.subject_mapping_type:
						subject = "<" + subject_value + ">"

					else:
						if triples_map.subject_map.condition == "":

							try:
								subject =  "\"" + triples_map.subject_map.value + "\""
								triple_entry = {subject: [dictionary_maker_xml(row)]}	
								triples_map_triples.update(triple_entry) 
							except:
								subject = None

						else:
						#	field, condition = condition_separetor(triples_map.subject_map.condition)
						#	if row[field] == condition:
							try:
								subject =  "\"" + triples_map.subject_map.value + "\""
								triple_entry = {subject: [dictionary_maker_xml(row)]}
								triples_map_triples.update(triple_entry) 
							except:
								subject = None

			else:
				if triples_map.subject_map.condition == "":

					try:
						subject = "<" + subject_value  + ">"
					except:
						subject = None

				else:
				#	field, condition = condition_separetor(triples_map.subject_map.condition)
				#	if row[field] == condition:
					try:
						subject = "<" + subject_value  + ">"
					except:
						subject = None

			if triples_map.subject_map.rdf_class is not None and subject is not None:
				rdf_type = subject + " <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> " + "<{}>.\n".format(triples_map.subject_map.rdf_class)
				if triples_map.subject_map.graph is not None:
					if "{" in triples_map.subject_map.graph:	
						rdf_type = rdf_type[:-2] + " <" + string_substitution_xml(triples_map.subject_map.graph, "{(.+?)}", child, "subject") + "> .\n"
					else:
						rdf_type = rdf_type[:-2] + " <" + triples_map.subject_map.graph + "> .\n"
				if duplicate == "yes":
					if rdf_type not in generated_triples:
						output_file_descriptor.write(rdf_type)
						csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
						generated_triples.update({rdf_type : number_triple + i + 1})
						i += 1
				else:
					output_file_descriptor.write(rdf_type)
					csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
					i += 1


			for predicate_object_map in triples_map.predicate_object_maps_list:
				if predicate_object_map.predicate_map.mapping_type == "constant" or predicate_object_map.predicate_map.mapping_type == "constant shortcut":
					predicate = "<" + predicate_object_map.predicate_map.value + ">"
				elif predicate_object_map.predicate_map.mapping_type == "template":
					if predicate_object_map.predicate_map.condition != "":
							#field, condition = condition_separetor(predicate_object_map.predicate_map.condition)
							#if row[field] == condition:
							try:
								predicate = "<" + string_substitution_xml(predicate_object_map.predicate_map.value, "{(.+?)}", child, "predicate") + ">"
							except:
								predicate = None
							#else:
							#	predicate = None
					else:
						try:
							predicate = "<" + string_substitution_xml(predicate_object_map.predicate_map.value, "{(.+?)}", child, "predicate") + ">"
						except:
							predicate = None
				elif predicate_object_map.predicate_map.mapping_type == "reference":
						if predicate_object_map.predicate_map.condition != "":
							#field, condition = condition_separetor(predicate_object_map.predicate_map.condition)
							#if row[field] == condition:
							predicate = string_substitution_xml(predicate_object_map.predicate_map.value, ".+", child, "predicate")
							#else:
							#	predicate = None
						else:
							predicate = string_substitution_xml(predicate_object_map.predicate_map.value, ".+", child, "predicate")
				else:
					predicate = None

				if predicate_object_map.object_map.mapping_type == "constant" or predicate_object_map.object_map.mapping_type == "constant shortcut":
					if "/" in predicate_object_map.object_map.value:
						object = "<" + predicate_object_map.object_map.value + ">"
					else:
						object = "\"" + predicate_object_map.object_map.value + "\""
				elif predicate_object_map.object_map.mapping_type == "template":
					try:
						if predicate_object_map.object_map.term is None:
							object = "<" + string_substitution(predicate_object_map.object_map.value, "{(.+?)}", row, "object") + ">"
						elif "IRI" in predicate_object_map.object_map.term:
							object = "<" + string_substitution(predicate_object_map.object_map.value, "{(.+?)}", row, "object") + ">"
						else:
							object = "\"" + string_substitution(predicate_object_map.object_map.value, "{(.+?)}", row, "object") + "\""
					except TypeError:
						object = None
				elif predicate_object_map.object_map.mapping_type == "reference":
					object = string_substitution_xml(predicate_object_map.object_map.value, ".+", child, "object")
					if (predicate_object_map.object_map.language is not None) and (object is not None):
						if "spanish" in predicate_object_map.object_map.language or "es" in predicate_object_map.object_map.language :
							object += "@es"
						elif "english" in predicate_object_map.object_map.language or "en" in predicate_object_map.object_map.language :
							object += "@en"
						elif "IRI" in predicate_object_map.object_map.term:
							object = "<" + object + ">" 
				elif predicate_object_map.object_map.mapping_type == "parent triples map":
					if subject is not None:
						for triples_map_element in triples_map_list:
							if triples_map_element.triples_map_id == predicate_object_map.object_map.value:
								if triples_map_element.data_source != triples_map.data_source:
									if triples_map_element.triples_map_id + "_" + predicate_object_map.object_map.child not in join_table:
										if str(triples_map_element.file_format).lower() == "csv" or triples_map_element.file_format == "JSONPath":
											with open(str(triples_map_element.data_source), "r") as input_file_descriptor:
												if str(triples_map_element.file_format).lower() == "csv":
													data = csv.DictReader(input_file_descriptor, delimiter=delimiter)
													hash_maker(data, triples_map_element, predicate_object_map.object_map)
												else:
													data = json.load(input_file_descriptor)
													hash_maker(data[list(data.keys())[0]], triples_map_element, predicate_object_map.object_map)

										elif triples_map_element.file_format == "XPath":
											with open(str(triples_map_element.data_source), "r") as input_file_descriptor:
												child_tree = ET.parse(input_file_descriptor)
												child_root = child_tree.getroot()
												hash_maker_xml(child_root, triples_map_element, predicate_object_map.object_map)							
										else:
											database, query_list = translate_sql(triples_map)
											db = connector.connect(host=host, port=port, user=user, password=password)
											cursor = db.cursor()
											cursor.execute("use " + database)
											for query in query_list:
												cursor.execute(query)
											hash_maker_array(cursor, triples_map_element, predicate_object_map.object_map)

									if child.find(predicate_object_map.object_map.child[0]) is not None:
										if child.find(predicate_object_map.object_map.child[0]).text in join_table[triples_map_element.triples_map_id + "_" + predicate_object_map.object_map.child[0]]:
											object_list = join_table[triples_map_element.triples_map_id + "_" + predicate_object_map.object_map.child[0]][child.find(predicate_object_map.object_map.child[0]).text]
										else:
											object_list = []
									object = None
								else:
									if predicate_object_map.object_map.parent is not None:
										if triples_map_element.triples_map_id + "_" + predicate_object_map.object_map.child not in join_table:
											with open(str(triples_map_element.data_source), "r") as input_file_descriptor:
												if str(triples_map_element.file_format).lower() == "csv":
													data = csv.DictReader(input_file_descriptor, delimiter=delimiter)
													hash_maker(data, triples_map_element, predicate_object_map.object_map)
												else:
													data = json.load(input_file_descriptor)
													hash_maker(data[list(data.keys())[0]], triples_map_element, predicate_object_map.object_map)
										if 	predicate_object_map.object_map.child[0] in row.keys():
											if row[predicate_object_map.object_map.child[0]] in join_table[triples_map_element.triples_map_id + "_" + predicate_object_map.object_map.child[0]]:
												object_list = join_table[triples_map_element.triples_map_id + "_" + predicate_object_map.object_map.child[0]][row[predicate_object_map.object_map.child[0]]]
											else:
												object_list = []
										object = None
									else:
										try:
											object = "<" + string_substitution_xml(triples_map_element.subject_map.value, "{(.+?)}", child, "object") + ">"
										except TypeError:
											object = None
								break
							else:
								continue
					else:
						object = None
				else:
					object = None

				
				if object is not None and predicate_object_map.object_map.datatype is not None:
					object += "^^<{}>".format(predicate_object_map.object_map.datatype)

				if predicate is not None and object is not None and subject is not None:
					triple = subject + " " + predicate + " " + object + ".\n"
					if triples_map.subject_map.graph is not None:
						if "{" in triples_map.subject_map.graph:
							triple = triple[:-2] + " <" + string_substitution_xml(triples_map.subject_map.graph, "{(.+?)}", child, "subject") + ">.\n"
						else:
							triple = triple[:-2] + " <" + triples_map.subject_map.graph + ">.\n"
					if duplicate == "yes":
						if triple not in generated_triples:
							output_file_descriptor.write(triple)
							csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
							generated_triples.update({triple : number_triple})
							i += 1
					else:
						output_file_descriptor.write(triple)
						csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
						i += 1
				elif predicate is not None and subject is not None and object_list:
					for obj in object_list:
						if predicate_object_map.object_map.term is not None:
							if "IRI" in predicate_object_map.object_map.term:
								triple = subject + " " + predicate + " <" + obj[1:-1] + ">.\n"
							else:
								triple = subject + " " + predicate + " " + obj + ".\n"
						else:
							triple = subject + " " + predicate + " " + obj + ".\n"

						if triples_map.subject_map.graph is not None:
							if "{" in triples_map.subject_map.graph:
								triple = triple[:-2] + " <" + string_substitution_xml(triples_map.subject_map.graph, "{(.+?)}", child, "subject") + ">.\n"
							else:
								triple = triple[:-2] + " <" + triples_map.subject_map.graph + ">.\n"

						if duplicate == "yes":
							if triple not in generated_triples:
								output_file_descriptor.write(triple)
								csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
								generated_triples.update({triple : number_triple})
								i += 1
						else:
							output_file_descriptor.write(triple)
							csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
							i += 1
					object_list = []
				else:
					continue

				 	 	

	return i

def semantify_file_array(triples_map, triples_map_list, delimiter, output_file_descriptor, csv_file, dataset_name, data):
	triple_array = []
	object_list = []

	i = 0
	for row in data:
		subject_value = string_substitution(triples_map.subject_map.value, "{(.+?)}", row, "subject") 	
		if triples_map.subject_map.condition == "":
			try:
				subject = "<" + subject_value  + ">"
			except:
				subject = None

		else:
		#	field, condition = condition_separetor(triples_map.subject_map.condition)
		#	if row[field] == condition:
			try:
				subject = "<" + subject_value  + ">"
			except:
				subject = None

		if triples_map.subject_map.rdf_class is not None and subject is not None:
			rdf_type = subject + " <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> " + "<{}>.\n".format(triples_map.subject_map.rdf_class)
			if duplicate == "yes":
				if rdf_type not in generated_triples:
					output_file_descriptor.write(rdf_type)
					csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
					generated_triples.update({rdf_type : number_triple + i + 1})
					i += 1
			else:
				output_file_descriptor.write(rdf_type)
				csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
				i += 1


		for predicate_object_map in triples_map.predicate_object_maps_list:
			if predicate_object_map.predicate_map.mapping_type == "constant" or predicate_object_map.predicate_map.mapping_type == "constant shortcut":
				predicate = "<" + predicate_object_map.predicate_map.value + ">"
			elif predicate_object_map.predicate_map.mapping_type == "template":
				if predicate_object_map.predicate_map.condition != "":
						#field, condition = condition_separetor(predicate_object_map.predicate_map.condition)
						#if row[field] == condition:
						try:
							predicate = "<" + string_substitution(predicate_object_map.predicate_map.value, "{(.+?)}", row, "predicate") + ">"
						except:
							predicate = None
						#else:
						#	predicate = None
				else:
					try:
						predicate = "<" + string_substitution(predicate_object_map.predicate_map.value, "{(.+?)}", row, "predicate") + ">"
					except:
						predicate = None
			elif predicate_object_map.predicate_map.mapping_type == "reference":
					if predicate_object_map.predicate_map.condition != "":
						#field, condition = condition_separetor(predicate_object_map.predicate_map.condition)
						#if row[field] == condition:
						predicate = string_substitution(predicate_object_map.predicate_map.value, ".+", row, "predicate")
						#else:
						#	predicate = None
					else:
						predicate = string_substitution(predicate_object_map.predicate_map.value, ".+", row, "predicate")
			else:
				predicate = None

			if predicate_object_map.object_map.mapping_type == "constant" or predicate_object_map.object_map.mapping_type == "constant shortcut":
				object = "<" + predicate_object_map.object_map.value + ">"
			elif predicate_object_map.object_map.mapping_type == "template":
				try:
					if predicate_object_map.object_map.term is None:
						object = "<" + string_substitution(predicate_object_map.object_map.value, "{(.+?)}", row, "object") + ">"
					elif "IRI" in predicate_object_map.object_map.term:
						object = "<" + string_substitution(predicate_object_map.object_map.value, "{(.+?)}", row, "object") + ">"
					else:
						object = "\"" + string_substitution(predicate_object_map.object_map.value, "{(.+?)}", row, "object") + "\""
				except TypeError:
					object = None
			elif predicate_object_map.object_map.mapping_type == "reference":
				object = string_substitution(predicate_object_map.object_map.value, ".+", row, "object")
			elif predicate_object_map.object_map.mapping_type == "parent triples map":
				if subject is not None:
					for triples_map_element in triples_map_list:
						if triples_map_element.triples_map_id == predicate_object_map.object_map.value:
							if triples_map_element.data_source != triples_map.data_source:
								if triples_map_element.triples_map_id + "_" + predicate_object_map.object_map.child not in join_table:
									if str(triples_map_element.file_format).lower() == "csv" or triples_map_element.file_format == "JSONPath":
										with open(str(triples_map_element.data_source), "r") as input_file_descriptor:
											if str(triples_map_element.file_format).lower() == "csv":
												data = csv.DictReader(input_file_descriptor, delimiter=delimiter)
											else:
												data = json.load(input_file_descriptor)
											hash_maker(data, triples_map_element, predicate_object_map.object_map)							
									else:
										database, query_list = translate_sql(triples_map)
										db = connector.connect(host=host, port=port, user=user, password=password)
										cursor = db.cursor()
										cursor.execute("use " + database)
										for query in query_list:
											cursor.execute(query)
										hash_maker_array(cursor, triples_map_element, predicate_object_map.object_map)
								
								if sublist(predicate_object_map.object_map.child,row.keys()):
									if child_list_value(predicate_object_map.object_map.child,row) in join_table[triples_map_element.triples_map_id + "_" + child_list(predicate_object_map.object_map.child)]:
										object_list = join_table[triples_map_element.triples_map_id + "_" + child_list(predicate_object_map.object_map.child)][child_list_value(predicate_object_map.object_map.child,row)]
									else:
										object_list = []
								object = None
							else:
								try:
									object = "<" + string_substitution(triples_map_element.subject_map.value, "{(.+?)}", row, "object") + ">"
								except TypeError:
									object = None
							break
						else:
							continue
				else:
					object = None
			else:
				object = None


			if object is not None and predicate_object_map.object_map.datatype is not None:
				object += "^^<{}>".format(predicate_object_map.object_map.datatype)

			if predicate is not None and object is not None and subject is not None:
				triple = subject + " " + predicate + " " + object + ".\n"
				if duplicate == "yes":
					if triple not in triple_array:
						output_file_descriptor.write(triple)
						csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
						triple_array.append(triple)
						i += 1
				else:
					output_file_descriptor.write(triple)
					csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
					i += 1
			elif predicate is not None and subject is not None and object_list:
				for obj in object_list:
					if predicate_object_map.object_map.term is not None:
						if "IRI" in predicate_object_map.object_map.term:
							triple = subject + " " + predicate + " <" + obj[1:-1] + ">.\n"
						else:
							triple = subject + " " + predicate + " " + obj + ".\n"
					else:
						triple = subject + " " + predicate + " " + obj + ".\n"
					if duplicate == "yes":
						if triple not in triple_array:
							output_file_descriptor.write(triple)
							csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
							triple_array.append(triple)
							i += 1
					else:
						output_file_descriptor.write(triple)
						csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
						i += 1
				object_list = []
			else:
				continue
	return i

def semantify_json(triples_map, triples_map_list, delimiter, output_file_descriptor, csv_file, dataset_name, data):

	triples_map_triples = {}
	generated_triples = {}
	object_list = []
	
	i = 0
	subject_value = string_substitution_json(triples_map.subject_map.value, "{(.+?)}", data, "subject") 	
	if duplicate == "yes":
		triple_entry = {subject_value: [dictionary_maker(data)]}	
		if subject_value in triples_map_triples:
			if dictionary_maker(data) in triples_map_triples[subject_value]:
				subject = None
			else:
				if triples_map.subject_map.subject_mapping_type == "template":
					if triples_map.subject_map.term_type is None:
						if triples_map.subject_map.condition == "":

							try:
								subject = "<" + subject_value + ">"
								triples_map_triples[subject_value].append(dictionary_maker(data)) 
							except:
								subject = None

						else:
						#	field, condition = condition_separetor(triples_map.subject_map.condition)
						#	if row[field] == condition:
							try:
								subject = "<" + subject_value  + ">"
								triples_map_triples[subject_value].append(dictionary_maker(data)) 
							except:
								subject = None 
					else:
						if "IRI" in triples_map.subject_map.term_type:
							if triples_map.subject_map.condition == "":

								try:
									subject = "<http://example.com/base/" + subject_value + ">"
									triples_map_triples[subject_value].append(dictionary_maker(data)) 
								except:
									subject = None

							else:
							#	field, condition = condition_separetor(triples_map.subject_map.condition)
							#	if row[field] == condition:
								try:
									subject = "<http://example.com/base/" + subject_value + ">"
									triples_map_triples[subject_value].append(dictionary_maker(data)) 
								except:
									subject = None 

						elif "BlankNode" in triples_map.subject_map.term_type:
							if triples_map.subject_map.condition == "":

								try:
									subject = "_:" + subject_value
									triples_map_triples[subject_value].append(dictionary_maker(data)) 
								except:
									subject = None

							else:
							#	field, condition = condition_separetor(triples_map.subject_map.condition)
							#	if row[field] == condition:
								try:
									subject = "_:" + subject_value  
									triples_map_triples[subject_value].append(dictionary_maker(data)) 
								except:
									subject = None
									
						else:
							if triples_map.subject_map.condition == "":

								try:
									subject = "<" + subject_value + ">"
									triples_map_triples.update(triple_entry) 
								except:
									subject = None

							else:
							#	field, condition = condition_separetor(triples_map.subject_map.condition)
							#	if row[field] == condition:
								try:
									subject = "<" + subject_value + ">"
									triples_map_triples.update(triple_entry) 
								except:
									subject = None 
				elif "reference" in triples_map.subject_map.subject_mapping_type:
					subject_value = string_substitution_json(triples_map.subject_map.value, ".+", data, "subject")
					subject_value = subject_value[1:-1]
					if "/" in subject_value:
						i = len(subject_value) - 1
						temp = ""
						while  0 < i:
							if subject_value[i] == "/":
								break
							else:
								temp = subject_value[i] + temp
							i -= 1
						subject_value = temp
					if triples_map.subject_map.condition == "":

						try:
							subject = "<http://example.com/base/" + subject_value + ">"
							triples_map_triples.update(triple_entry) 
						except:
							subject = None

					else:
					#	field, condition = condition_separetor(triples_map.subject_map.condition)
					#	if row[field] == condition:
						try:
							subject = "<http://example.com/base/" + subject_value + ">"
							triples_map_triples.update(triple_entry) 
						except:
							subject = None

				elif "constant" in triples_map.subject_map.subject_mapping_type:
						subject = "<" + subject_value + ">"
				else:
					if triples_map.subject_map.condition == "":

						try:
							subject = "\"" + triples_map.subject_map.value + "\""
							triple_entry = {subject: [dictionary_maker(data)]}	
							triples_map_triples.update(triple_entry) 
						except:
							subject = None

					else:
					#	field, condition = condition_separetor(triples_map.subject_map.condition)
					#	if row[field] == condition:
						try:
							subject = "\"" + triples_map.subject_map.value + "\""
							triple_entry = {subject: [dictionary_maker(data)]}
							triples_map_triples.update(triple_entry) 
						except:
							subject = None
		else:
			if triples_map.subject_map.subject_mapping_type == "template":
				if triples_map.subject_map.term_type is None:
					if triples_map.subject_map.condition == "":

						try:
							subject = "<" + subject_value + ">"
							triples_map_triples.update(triple_entry) 
						except:
							subject = None

					else:
					#	field, condition = condition_separetor(triples_map.subject_map.condition)
					#	if row[field] == condition:
						try:
							subject = "<" + subject_value  + ">"
							triples_map_triples.update(triple_entry) 
						except:
							subject = None
				else:
					if "IRI" in triples_map.subject_map.term_type:
						if triples_map.subject_map.condition == "":

							try:
								subject = "<http://example.com/base/" + subject_value + ">"
								triples_map_triples.update(triple_entry) 
							except:
								subject = None

						else:
						#	field, condition = condition_separetor(triples_map.subject_map.condition)
						#	if row[field] == condition:
							try:
								subject = "<http://example.com/base/" + subject_value + ">"
								triples_map_triples.update(triple_entry) 
							except:
								subject = None
						
					elif "BlankNode" in triples_map.subject_map.term_type:
						if triples_map.subject_map.condition == "":

							try:
								subject = "_:" + subject_value 
								triples_map_triples.update(triple_entry) 
							except:
								subject = None

						else:
						#	field, condition = condition_separetor(triples_map.subject_map.condition)
						#	if row[field] == condition:
							try:
								subject = "_:" + subject_value 
								triples_map_triples.update(triple_entry) 
							except:
								subject = None
					else:
						if triples_map.subject_map.condition == "":

							try:
								subject = "<" + subject_value + ">"
								triples_map_triples.update(triple_entry) 
							except:
								subject = None

						else:
						#	field, condition = condition_separetor(triples_map.subject_map.condition)
						#	if row[field] == condition:
							try:
								subject = "<" + subject_value + ">"
								triples_map_triples.update(triple_entry) 
							except:
								subject = None

			elif "reference" in triples_map.subject_map.subject_mapping_type:
				if triples_map.subject_map.condition == "":
					subject_value = string_substitution_json(triples_map.subject_map.value, ".+", data, "subject")
					subject_value = subject_value[1:-1]
					if "/" in subject_value:
						i = len(subject_value) - 1
						temp = ""
						while  0 < i:
							if subject_value[i] == "/":
								break
							else:
								temp = subject_value[i] + temp 
							i -= 1
						subject_value = temp
					try:
						subject = "<http://example.com/base/" + subject_value + ">"
						triples_map_triples.update(triple_entry) 
					except:
						subject = None

				else:
				#	field, condition = condition_separetor(triples_map.subject_map.condition)
				#	if row[field] == condition:
					try:
						subject = "<http://example.com/base/" + subject_value + ">"
						triples_map_triples.update(triple_entry) 
					except:
						subject = None

			elif "constant" in triples_map.subject_map.subject_mapping_type:
						subject = "<" + subject_value + ">"

			else:
				if triples_map.subject_map.condition == "":

					try:
						subject =  "\"" + triples_map.subject_map.value + "\""
						triple_entry = {subject: [dictionary_maker(data)]}	
						triples_map_triples.update(triple_entry) 
					except:
						subject = None

				else:
				#	field, condition = condition_separetor(triples_map.subject_map.condition)
				#	if row[field] == condition:
					try:
						subject =  "\"" + triples_map.subject_map.value + "\""
						triple_entry = {subject: [dictionary_maker(data)]}
						triples_map_triples.update(triple_entry) 
					except:
						subject = None

	else:
		if triples_map.subject_map.condition == "":

			try:
				subject = "<" + subject_value  + ">"
			except:
				subject = None

		else:
		#	field, condition = condition_separetor(triples_map.subject_map.condition)
		#	if row[field] == condition:
			try:
				subject = "<" + subject_value  + ">"
			except:
				subject = None

	if triples_map.subject_map.rdf_class is not None and subject is not None:
		rdf_type = subject + " <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> " + "<{}>.\n".format(triples_map.subject_map.rdf_class)
		if triples_map.subject_map.graph is not None:
			if "{" in triples_map.subject_map.graph:	
				rdf_type = rdf_type[:-2] + " <" + string_substitution_json(triples_map.subject_map.graph, "{(.+?)}", data, "subject") + "> .\n"
			else:
				rdf_type = rdf_type[:-2] + " <" + triples_map.subject_map.graph + "> .\n"
		if duplicate == "yes":
			if rdf_type not in generated_triples:
				output_file_descriptor.write(rdf_type)
				csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
				generated_triples.update({rdf_type : number_triple + i + 1})
				i += 1
		else:
			output_file_descriptor.write(rdf_type)
			csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
			i += 1

	
	for predicate_object_map in triples_map.predicate_object_maps_list:
		if predicate_object_map.predicate_map.mapping_type == "constant" or predicate_object_map.predicate_map.mapping_type == "constant shortcut":
			predicate = "<" + predicate_object_map.predicate_map.value + ">"
		elif predicate_object_map.predicate_map.mapping_type == "template":
			if predicate_object_map.predicate_map.condition != "":
					#field, condition = condition_separetor(predicate_object_map.predicate_map.condition)
					#if row[field] == condition:
					try:
						predicate = "<" + string_substitution_json(predicate_object_map.predicate_map.value, "{(.+?)}", data, "predicate") + ">"
					except:
						predicate = None
					#else:
					#	predicate = None
			else:
				try:
					predicate = "<" + string_substitution_json(predicate_object_map.predicate_map.value, "{(.+?)}", data, "predicate") + ">"
				except:
					predicate = None
		elif predicate_object_map.predicate_map.mapping_type == "reference":
				if predicate_object_map.predicate_map.condition != "":
					#field, condition = condition_separetor(predicate_object_map.predicate_map.condition)
					#if row[field] == condition:
					predicate = string_substitution_json(predicate_object_map.predicate_map.value, ".+", data, "predicate")
					#else:
					#	predicate = None
				else:
					predicate = string_substitution_json(predicate_object_map.predicate_map.value, ".+", data, "predicate")
		else:
			predicate = None

		if predicate_object_map.object_map.mapping_type == "constant" or predicate_object_map.object_map.mapping_type == "constant shortcut":
			if "/" in predicate_object_map.object_map.value:
				object = "<" + predicate_object_map.object_map.value + ">"
			else:
				object = "\"" + predicate_object_map.object_map.value + "\""
		elif predicate_object_map.object_map.mapping_type == "template":
			try:
				if predicate_object_map.object_map.term is None:
					object = "<" + string_substitution(predicate_object_map.object_map.value, "{(.+?)}", row, "object") + ">"
				elif "IRI" in predicate_object_map.object_map.term:
					object = "<" + string_substitution(predicate_object_map.object_map.value, "{(.+?)}", row, "object") + ">"
				else:
					object = "\"" + string_substitution(predicate_object_map.object_map.value, "{(.+?)}", row, "object") + "\""
			except TypeError:
				object = None
		elif predicate_object_map.object_map.mapping_type == "reference":
			object = string_substitution_json(predicate_object_map.object_map.value, ".+", data, "object")
			if (predicate_object_map.object_map.language is not None) and (object is not None):
				if "spanish" in predicate_object_map.object_map.language or "es" in predicate_object_map.object_map.language :
					object += "@es"
				elif "english" in predicate_object_map.object_map.language or "en" in predicate_object_map.object_map.language :
					object += "@en"
				elif "IRI" in predicate_object_map.object_map.term:
						object = "<" + object + ">" 
		elif predicate_object_map.object_map.mapping_type == "parent triples map":
			if subject is not None:
				for triples_map_element in triples_map_list:
					if triples_map_element.triples_map_id == predicate_object_map.object_map.value:
						if triples_map_element.data_source != triples_map.data_source:
							if triples_map_element.triples_map_id + "_" + predicate_object_map.object_map.child not in join_table:
								if str(triples_map_element.file_format).lower() == "csv" or triples_map_element.file_format == "JSONPath":
									with open(str(triples_map_element.data_source), "r") as input_file_descriptor:
										if str(triples_map_element.file_format).lower() == "csv":
											data = csv.DictReader(input_file_descriptor, delimiter=delimiter)
											hash_maker(data, triples_map_element, predicate_object_map.object_map)
										else:
											data = json.load(input_file_descriptor)
											hash_maker(data[list(data.keys())[0]], triples_map_element, predicate_object_map.object_map)							
								else:
									database, query_list = translate_sql(triples_map)
									db = connector.connect(host=host, port=port, user=user, password=password)
									cursor = db.cursor()
									cursor.execute("use " + database)
									for query in query_list:
										cursor.execute(query)
									hash_maker_array(cursor, triples_map_element, predicate_object_map.object_map)
							
							if sublist(predicate_object_map.object_map.child,data.keys()):
								if child_list_value(predicate_object_map.object_map.child,data) in join_table[triples_map_element.triples_map_id + "_" + child_list(predicate_object_map.object_map.child)]:
									object_list = join_table[triples_map_element.triples_map_id + "_" + child_list(predicate_object_map.object_map.child)][child_list_value(predicate_object_map.object_map.child,data)]
								else:
									object_list = []
							object = None
						else:
							if predicate_object_map.object_map.parent is not None:
								if triples_map_element.triples_map_id + "_" + predicate_object_map.object_map.child not in join_table:
									with open(str(triples_map_element.data_source), "r") as input_file_descriptor:
										if str(triples_map_element.file_format).lower() == "csv":
											data = csv.DictReader(input_file_descriptor, delimiter=delimiter)
											hash_maker(data, triples_map_element, predicate_object_map.object_map)
										else:
											data = json.load(input_file_descriptor)
											hash_maker(data[list(data.keys())[0]], triples_map_element, predicate_object_map.object_map)
								if 	predicate_object_map.object_map.child in data.keys():
									if data[predicate_object_map.object_map.child] in join_table[triples_map_element.triples_map_id + "_" + predicate_object_map.object_map.child]:
										object_list = join_table[triples_map_element.triples_map_id + "_" + predicate_object_map.object_map.child][data[predicate_object_map.object_map.child]]
									else:
										object_list = []
								object = None
							else:
								try:
									object = "<" + string_substitution_json(triples_map_element.subject_map.value, "{(.+?)}", data, "object") + ">"
								except TypeError:
									object = None
						break
					else:
						continue
			else:
				object = None
		else:
			object = None

		
		if object is not None and predicate_object_map.object_map.datatype is not None:
			object = "\"" + object[1:-1] + "\"" + "^^<{}>".format(predicate_object_map.object_map.datatype)

		if predicate is not None and object is not None and subject is not None:
			triple = subject + " " + predicate + " " + object + ".\n"
			if triples_map.subject_map.graph is not None:
				if "{" in triples_map.subject_map.graph:
					triple = triple[:-2] + " <" + string_substitution_json(triples_map.subject_map.graph, "{(.+?)}", data, "subject") + ">.\n"
				else:
					triple = triple[:-2] + " <" + triples_map.subject_map.graph + ">.\n"
			if duplicate == "yes":
				if triple not in generated_triples:
					output_file_descriptor.write(triple)
					csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
					generated_triples.update({triple : number_triple})
					i += 1
			else:
				output_file_descriptor.write(triple)
				csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
				i += 1
		elif predicate is not None and subject is not None and object_list:
			for obj in object_list:
				if predicate_object_map.object_map.term is not None:
					if "IRI" in predicate_object_map.object_map.term:
						triple = subject + " " + predicate + " <" + obj[1:-1] + ">.\n"
					else:
						triple = subject + " " + predicate + " " + obj + ".\n"
				else:
					triple = subject + " " + predicate + " " + obj + ".\n"
				if triples_map.subject_map.graph is not None:
					if "{" in triples_map.subject_map.graph:
						triple = triple[:-2] + " <" + string_substitution_json(triples_map.subject_map.graph, "{(.+?)}", data, "subject") + ">.\n"
					else:
						triple = triple[:-2] + " <" + triples_map.subject_map.graph + ">.\n"
				if duplicate == "yes":
					if triple not in generated_triples:
						output_file_descriptor.write(triple)
						csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
						generated_triples.update({triple : number_triple})
						i += 1
				else:
					output_file_descriptor.write(triple)
					csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
					i += 1
			object_list = []
		else:
			continue
	return i

def semantify_file(triples_map, triples_map_list, delimiter, output_file_descriptor, csv_file, dataset_name, data):
	
	print("\n\nTM:",triples_map.triples_map_name)

	"""
	(Private function, not accessible from outside this package)

	Takes a triples-map rule and applies it to each one of the rows of its CSV data
	source

	Parameters
	----------
	triples_map : TriplesMap object
		Mapping rule consisting of a logical source, a subject-map and several predicateObjectMaps
		(refer to the TriplesMap.py file in the triplesmap folder)
	triples_map_list : list of TriplesMap objects
		List of triples-maps parsed from current mapping being used for the semantification of a
		dataset (mainly used to perform rr:joinCondition mappings)
	delimiter : string
		Delimiter value for the CSV or TSV file ("\s" and "\t" respectively)
	output_file_descriptor : file object 
		Descriptor to the output file (refer to the Python 3 documentation)

	Returns
	-------
	An .nt file per each dataset mentioned in the configuration file semantified.
	If the duplicates are asked to be removed in main memory, also returns a -min.nt
	file with the triples sorted and with the duplicates removed.
	"""
	triples_map_triples = {}
	generated_triples = {}
	object_list = []
	
	i = 0
	for row in data:
		subject_value = string_substitution(triples_map.subject_map.value, "{(.+?)}", row, "subject") 	
		if duplicate == "yes":
			triple_entry = {subject_value: [dictionary_maker(row)]}	
			if subject_value in triples_map_triples:
				if dictionary_maker(row) in triples_map_triples[subject_value]:
					subject = None
				else:
					if triples_map.subject_map.subject_mapping_type == "template":
						if triples_map.subject_map.term_type is None:
							if triples_map.subject_map.condition == "":

								try:
									subject = "<" + subject_value + ">"
									triples_map_triples[subject_value].append(dictionary_maker(row)) 
								except:
									subject = None

							else:
							#	field, condition = condition_separetor(triples_map.subject_map.condition)
							#	if row[field] == condition:
								try:
									subject = "<" + subject_value  + ">"
									triples_map_triples[subject_value].append(dictionary_maker(row)) 
								except:
									subject = None 
						else:
							if "IRI" in triples_map.subject_map.term_type:
								if triples_map.subject_map.condition == "":

									try:
										subject = "<http://example.com/base/" + subject_value + ">"
										triples_map_triples[subject_value].append(dictionary_maker(row)) 
									except:
										subject = None

								else:
								#	field, condition = condition_separetor(triples_map.subject_map.condition)
								#	if row[field] == condition:
									try:
										subject = "<http://example.com/base/" + subject_value + ">"
										triples_map_triples[subject_value].append(dictionary_maker(row)) 
									except:
										subject = None 

							elif "BlankNode" in triples_map.subject_map.term_type:
								if triples_map.subject_map.condition == "":

									try:
										subject = "_:" + subject_value
										triples_map_triples[subject_value].append(dictionary_maker(row)) 
									except:
										subject = None

								else:
								#	field, condition = condition_separetor(triples_map.subject_map.condition)
								#	if row[field] == condition:
									try:
										subject = "_:" + subject_value  
										triples_map_triples[subject_value].append(dictionary_maker(row)) 
									except:
										subject = None
										
							else:
								if triples_map.subject_map.condition == "":

									try:
										subject = "<" + subject_value + ">"
										triples_map_triples.update(triple_entry) 
									except:
										subject = None

								else:
								#	field, condition = condition_separetor(triples_map.subject_map.condition)
								#	if row[field] == condition:
									try:
										subject = "<" + subject_value + ">"
										triples_map_triples.update(triple_entry) 
									except:
										subject = None 
					elif "reference" in triples_map.subject_map.subject_mapping_type:
						subject_value = string_substitution(triples_map.subject_map.value, ".+", row, "subject")
						if subject_value is not None:
							subject_value = subject_value[1:-1]
							if "/" in subject_value:
								i = len(subject_value) - 1
								temp = ""
								while  0 < i:
									if subject_value[i] == "/":
										break
									else:
										temp = subject_value[i] + temp
									i -= 1
								subject_value = temp
							if triples_map.subject_map.condition == "":

								try:
									subject = "<http://example.com/base/" + subject_value + ">"
									triples_map_triples.update(triple_entry) 
								except:
									subject = None

						else:
						#	field, condition = condition_separetor(triples_map.subject_map.condition)
						#	if row[field] == condition:
							try:
								subject = "<http://example.com/base/" + subject_value + ">"
								triples_map_triples.update(triple_entry) 
							except:
								subject = None

					elif "constant" in triples_map.subject_map.subject_mapping_type:
						subject = "<" + subject_value + ">"

					else:
						if triples_map.subject_map.condition == "":

							try:
								subject = "\"" + triples_map.subject_map.value + "\""
								triple_entry = {subject: [dictionary_maker(row)]}	
								triples_map_triples.update(triple_entry) 
							except:
								subject = None

						else:
						#	field, condition = condition_separetor(triples_map.subject_map.condition)
						#	if row[field] == condition:
							try:
								subject = "\"" + triples_map.subject_map.value + "\""
								triple_entry = {subject: [dictionary_maker(row)]}
								triples_map_triples.update(triple_entry) 
							except:
								subject = None
			else:
				if triples_map.subject_map.subject_mapping_type == "template":
					if triples_map.subject_map.term_type is None:
						if triples_map.subject_map.condition == "":

							try:
								subject = "<" + subject_value + ">"
								triples_map_triples.update(triple_entry) 
							except:
								subject = None

						else:
						#	field, condition = condition_separetor(triples_map.subject_map.condition)
						#	if row[field] == condition:
							try:
								subject = "<" + subject_value  + ">"
								triples_map_triples.update(triple_entry) 
							except:
								subject = None
					else:
						if "IRI" in triples_map.subject_map.term_type:
							if triples_map.subject_map.condition == "":

								try:
									subject = "<http://example.com/base/" + subject_value + ">"
									triples_map_triples.update(triple_entry) 
								except:
									subject = None

							else:
							#	field, condition = condition_separetor(triples_map.subject_map.condition)
							#	if row[field] == condition:
								try:
									subject = "<http://example.com/base/" + subject_value + ">"
									triples_map_triples.update(triple_entry) 
								except:
									subject = None
							
						elif "BlankNode" in triples_map.subject_map.term_type:
							if triples_map.subject_map.condition == "":

								try:
									subject = "_:" + subject_value 
									triples_map_triples.update(triple_entry) 
								except:
									subject = None

							else:
							#	field, condition = condition_separetor(triples_map.subject_map.condition)
							#	if row[field] == condition:
								try:
									subject = "_:" + subject_value 
									triples_map_triples.update(triple_entry) 
								except:
									subject = None
						else:
							if triples_map.subject_map.condition == "":

								try:
									subject = "<" + subject_value + ">"
									triples_map_triples.update(triple_entry) 
								except:
									subject = None

							else:
							#	field, condition = condition_separetor(triples_map.subject_map.condition)
							#	if row[field] == condition:
								try:
									subject = "<" + subject_value + ">"
									triples_map_triples.update(triple_entry) 
								except:
									subject = None

				elif "reference" in triples_map.subject_map.subject_mapping_type:
					if triples_map.subject_map.condition == "":
						subject_value = string_substitution(triples_map.subject_map.value, ".+", row, "subject")
						subject_value = subject_value[1:-1]
						if "/" in subject_value:
							i = len(subject_value) - 1
							temp = ""
							while  0 < i:
								if subject_value[i] == "/":
									break
								else:
									temp = subject_value[i] + temp 
								i -= 1
							subject_value = temp
						try:
							subject = "<http://example.com/base/" + subject_value + ">"
							triples_map_triples.update(triple_entry) 
						except:
							subject = None

					else:
					#	field, condition = condition_separetor(triples_map.subject_map.condition)
					#	if row[field] == condition:
						try:
							subject = "<http://example.com/base/" + subject_value + ">"
							triples_map_triples.update(triple_entry) 
						except:
							subject = None

				elif "constant" in triples_map.subject_map.subject_mapping_type:
					subject = "<" + subject_value + ">"

				else:
					if triples_map.subject_map.condition == "":

						try:
							subject =  "\"" + triples_map.subject_map.value + "\""
							triple_entry = {subject: [dictionary_maker(row)]}	
							triples_map_triples.update(triple_entry) 
						except:
							subject = None

					else:
					#	field, condition = condition_separetor(triples_map.subject_map.condition)
					#	if row[field] == condition:
						try:
							subject =  "\"" + triples_map.subject_map.value + "\""
							triple_entry = {subject: [dictionary_maker(row)]}
							triples_map_triples.update(triple_entry) 
						except:
							subject = None

		else:
			if triples_map.subject_map.condition == "":

				try:
					subject = "<" + subject_value  + ">"
				except:
					subject = None

			else:
			#	field, condition = condition_separetor(triples_map.subject_map.condition)
			#	if row[field] == condition:
				try:
					subject = "<" + subject_value  + ">"
				except:
					subject = None

		if triples_map.subject_map.rdf_class is not None and subject is not None:
			rdf_type = subject + " <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> " + "<{}>.\n".format(triples_map.subject_map.rdf_class)
			if triples_map.subject_map.graph is not None:
				if "{" in triples_map.subject_map.graph:	
					rdf_type = rdf_type[:-2] + " <" + string_substitution(triples_map.subject_map.graph, "{(.+?)}", row, "subject") + "> .\n"
				else:
					rdf_type = rdf_type[:-2] + " <" + triples_map.subject_map.graph + "> .\n"
			if duplicate == "yes":
				if rdf_type not in generated_triples:
					output_file_descriptor.write(rdf_type)
					csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
					generated_triples.update({rdf_type : number_triple + i + 1})
					i += 1
			else:
				output_file_descriptor.write(rdf_type)
				csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
				i += 1

		
		for predicate_object_map in triples_map.predicate_object_maps_list:
			if predicate_object_map.predicate_map.mapping_type == "constant" or predicate_object_map.predicate_map.mapping_type == "constant shortcut":
				predicate = "<" + predicate_object_map.predicate_map.value + ">"
			elif predicate_object_map.predicate_map.mapping_type == "template":
				if predicate_object_map.predicate_map.condition != "":
						#field, condition = condition_separetor(predicate_object_map.predicate_map.condition)
						#if row[field] == condition:
						try:
							predicate = "<" + string_substitution(predicate_object_map.predicate_map.value, "{(.+?)}", row, "predicate") + ">"
						except:
							predicate = None
						#else:
						#	predicate = None
				else:
					try:
						predicate = "<" + string_substitution(predicate_object_map.predicate_map.value, "{(.+?)}", row, "predicate") + ">"
					except:
						predicate = None
			elif predicate_object_map.predicate_map.mapping_type == "reference":
					if predicate_object_map.predicate_map.condition != "":
						#field, condition = condition_separetor(predicate_object_map.predicate_map.condition)
						#if row[field] == condition:
						predicate = string_substitution(predicate_object_map.predicate_map.value, ".+", row, "predicate")
						#else:
						#	predicate = None
					else:
						predicate = string_substitution(predicate_object_map.predicate_map.value, ".+", row, "predicate")
			else:
				predicate = None

			if predicate_object_map.object_map.mapping_type == "constant" or predicate_object_map.object_map.mapping_type == "constant shortcut":
				if "/" in predicate_object_map.object_map.value:
					object = "<" + predicate_object_map.object_map.value + ">"
				else:
					object = "\"" + predicate_object_map.object_map.value + "\""
			elif predicate_object_map.object_map.mapping_type == "template":
				try:
					if predicate_object_map.object_map.term is None:
						object = "<" + string_substitution(predicate_object_map.object_map.value, "{(.+?)}", row, "object") + ">"
					elif "IRI" in predicate_object_map.object_map.term:
						object = "<" + string_substitution(predicate_object_map.object_map.value, "{(.+?)}", row, "object") + ">"
					else:
						object = "\"" + string_substitution(predicate_object_map.object_map.value, "{(.+?)}", row, "object") + "\""
				except TypeError:
					object = None
			elif predicate_object_map.object_map.mapping_type == "reference":
				object = string_substitution(predicate_object_map.object_map.value, ".+", row, "object")
				if (predicate_object_map.object_map.language is not None) and (object is not None):
					if "spanish" in predicate_object_map.object_map.language or "es" in predicate_object_map.object_map.language :
						object += "@es"
					elif "english" in predicate_object_map.object_map.language or "en" in predicate_object_map.object_map.language :
						object += "@en"
					elif "IRI" in predicate_object_map.object_map.term:
						object = "<" + object + ">" 
			elif predicate_object_map.object_map.mapping_type == "parent triples map":
				if subject is not None:
					for triples_map_element in triples_map_list:
						if triples_map_element.triples_map_id == predicate_object_map.object_map.value:
							if triples_map_element.data_source != triples_map.data_source:
								if len(predicate_object_map.object_map.child) == 1:
									if (triples_map_element.triples_map_id + "_" + predicate_object_map.object_map.child[0]) not in join_table:
										if str(triples_map_element.file_format).lower() == "csv" or triples_map_element.file_format == "JSONPath":
											with open(str(triples_map_element.data_source), "r") as input_file_descriptor:
												if str(triples_map_element.file_format).lower() == "csv":
													data = csv.DictReader(input_file_descriptor, delimiter=delimiter)
													hash_maker(data, triples_map_element, predicate_object_map.object_map)
												else:
													data = json.load(input_file_descriptor)
													hash_maker(data[list(data.keys())[0]], triples_map_element, predicate_object_map.object_map)							
										else:
											database, query_list = translate_sql(triples_map)
											db = connector.connect(host=host, port=port, user=user, password=password)
											cursor = db.cursor()
											cursor.execute("use " + database)
											for query in query_list:
												cursor.execute(query)
											hash_maker_array(cursor, triples_map_element, predicate_object_map.object_map)

									if sublist(predicate_object_map.object_map.child,row.keys()):
										if child_list_value(predicate_object_map.object_map.child,row) in join_table[triples_map_element.triples_map_id + "_" + predicate_object_map.object_map.child[0]]:
											object_list = join_table[triples_map_element.triples_map_id + "_" + predicate_object_map.object_map.child[0]][row[predicate_object_map.object_map.child[0]]]
										else:
											object_list = []
									object = None
								else:
									if (triples_map_element.triples_map_id + "_" + child_list(predicate_object_map.object_map.child)) not in join_table:
										if str(triples_map_element.file_format).lower() == "csv" or triples_map_element.file_format == "JSONPath":
											with open(str(triples_map_element.data_source), "r") as input_file_descriptor:
												if str(triples_map_element.file_format).lower() == "csv":
													data = csv.DictReader(input_file_descriptor, delimiter=delimiter)
													hash_maker_list(data, triples_map_element, predicate_object_map.object_map)
												else:
													data = json.load(input_file_descriptor)
													hash_maker_list(data[list(data.keys())[0]], triples_map_element, predicate_object_map.object_map)							
										else:
											database, query_list = translate_sql(triples_map)
											db = connector.connect(host=host, port=port, user=user, password=password)
											cursor = db.cursor()
											cursor.execute("use " + database)
											for query in query_list:
												cursor.execute(query)
											hash_maker_array(cursor, triples_map_element, predicate_object_map.object_map)
									if sublist(predicate_object_map.object_map.child,row.keys()):
										if child_list_value(predicate_object_map.object_map.child,row) in join_table[triples_map_element.triples_map_id + "_" + child_list(predicate_object_map.object_map.child)]:
											object_list = join_table[triples_map_element.triples_map_id + "_" + child_list(predicate_object_map.object_map.child)][child_list_value(predicate_object_map.object_map.child,row)]
										else:
											object_list = []
									object = None
							else:
								if predicate_object_map.object_map.parent is not None:
									if str(triples_map_element.triples_map_id) + "_" + str(predicate_object_map.object_map.child) not in join_table:
										with open(str(triples_map_element.data_source), "r") as input_file_descriptor:
											if str(triples_map_element.file_format).lower() == "csv":
												data = csv.DictReader(input_file_descriptor, delimiter=delimiter)
												hash_maker(data, triples_map_element, predicate_object_map.object_map)
											else:
												data = json.load(input_file_descriptor)
												hash_maker(data[list(data.keys())[0]], triples_map_element, predicate_object_map.object_map)
									if sublist(predicate_object_map.object_map.child,row.keys()):
										if child_list_value(predicate_object_map.object_map.child,row) in join_table[triples_map_element.triples_map_id + "_" + child_list(predicate_object_map.object_map.child)]:
											object_list = join_table[triples_map_element.triples_map_id + "_" + child_list(predicate_object_map.object_map.child)][child_list_value(predicate_object_map.object_map.child,row)]
										else:
											object_list = []
									object = None
								else:
									try:
										object = "<" + string_substitution(triples_map_element.subject_map.value, "{(.+?)}", row, "object") + ">"
									except TypeError:
										object = None
							break
						else:
							continue
				else:
					object = None
			else:
				object = None

			
			if object is not None and predicate_object_map.object_map.datatype is not None:
				object = "\"" + object[1:-1] + "\"" + "^^<{}>".format(predicate_object_map.object_map.datatype)

			if predicate is not None and object is not None and subject is not None:
				triple = subject + " " + predicate + " " + object + ".\n"
				if triples_map.subject_map.graph is not None:
					if "{" in triples_map.subject_map.graph:
						triple = triple[:-2] + " <" + string_substitution(triples_map.subject_map.graph, "{(.+?)}", row, "subject") + ">.\n"
					else:
						triple = triple[:-2] + " <" + triples_map.subject_map.graph + ">.\n"
				if duplicate == "yes":
					if triple not in generated_triples:
						output_file_descriptor.write(triple)
						csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
						generated_triples.update({triple : number_triple})
						i += 1
				else:
					output_file_descriptor.write(triple)
					csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
					i += 1
			elif predicate is not None and subject is not None and object_list:
				for obj in object_list:
					if obj is not None:
						if predicate_object_map.object_map.term is not None:
							if "IRI" in predicate_object_map.object_map.term:
								triple = subject + " " + predicate + " <" + obj[1:-1] + ">.\n"
							else:
								triple = subject + " " + predicate + " " + obj + ".\n"
						else:
							triple = subject + " " + predicate + " " + obj + ".\n"
						if triples_map.subject_map.graph is not None:
							if "{" in triples_map.subject_map.graph:
								triple = triple[:-2] + " <" + string_substitution(triples_map.subject_map.graph, "{(.+?)}", row, "subject") + ">.\n"
							else:
								triple = triple[:-2] + " <" + triples_map.subject_map.graph + ">.\n"
						if duplicate == "yes":
							if triple not in generated_triples:
								output_file_descriptor.write(triple)
								csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
								generated_triples.update({triple : number_triple})
								i += 1
						else:
							output_file_descriptor.write(triple)
							csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
							i += 1
				object_list = []
			else:
				continue
	return i

def semantify_mysql(row, row_headers, triples_map, triples_map_list, output_file_descriptor, csv_file, dataset_name):

	"""
	(Private function, not accessible from outside this package)

	Takes a triples-map rule and applies it to each one of the rows of its CSV data
	source

	Parameters
	----------
	triples_map : TriplesMap object
		Mapping rule consisting of a logical source, a subject-map and several predicateObjectMaps
		(refer to the TriplesMap.py file in the triplesmap folder)
	triples_map_list : list of TriplesMap objects
		List of triples-maps parsed from current mapping being used for the semantification of a
		dataset (mainly used to perform rr:joinCondition mappings)
	delimiter : string
		Delimiter value for the CSV or TSV file ("\s" and "\t" respectively)
	output_file_descriptor : file object 
		Descriptor to the output file (refer to the Python 3 documentation)

	Returns
	-------
	An .nt file per each dataset mentioned in the configuration file semantified.
	If the duplicates are asked to be removed in main memory, also returns a -min.nt
	file with the triples sorted and with the duplicates removed.
	"""
	triples_map_triples = {}
	generated_triples = {}
	object_list = []
	subject_value = string_substitution_array(triples_map.subject_map.value, "{(.+?)}", row, row_headers, "subject")
	i = 0
	if duplicate == "yes":
		triple_entry = {subject_value: dictionary_maker_array(row, row_headers)}
		if subject_value in triples_map_triples:
			if shared_items(triples_map_triples[subject_value], triple_entry) == len(triples_map_triples[subject_value]):
				subject = None
			else:
				if triples_map.subject_map.subject_mapping_type == "template":
					if triples_map.subject_map.term_type is None:
						if triples_map.subject_map.condition == "":

							try:
								subject = "<" + subject_value + ">"
								triples_map_triples[subject_value].append(dictionary_maker(row)) 
							except:
								subject = None

						else:
						#	field, condition = condition_separetor(triples_map.subject_map.condition)
						#	if row[field] == condition:
							try:
								subject = "<" + subject_value  + ">"
								triples_map_triples[subject_value].append(dictionary_maker(row)) 
							except:
								subject = None 
					else:
						if "IRI" in triples_map.subject_map.term_type:
							if triples_map.subject_map.condition == "":

								try:
									subject = "<http://example.com/base/" + subject_value + ">"
									triples_map_triples[subject_value].append(dictionary_maker(row)) 
								except:
									subject = None

							else:
							#	field, condition = condition_separetor(triples_map.subject_map.condition)
							#	if row[field] == condition:
								try:
									subject = "<http://example.com/base/" + subject_value + ">"
									triples_map_triples[subject_value].append(dictionary_maker(row)) 
								except:
									subject = None 

						elif "BlankNode" in triples_map.subject_map.term_type:
							if triples_map.subject_map.condition == "":

								try:
									subject = "_:" + subject_value
									triples_map_triples[subject_value].append(dictionary_maker(row)) 
								except:
									subject = None

							else:
							#	field, condition = condition_separetor(triples_map.subject_map.condition)
							#	if row[field] == condition:
								try:
									subject = "_:" + subject_value  
									triples_map_triples[subject_value].append(dictionary_maker(row)) 
								except:
									subject = None
									
						else:
							if triples_map.subject_map.condition == "":

								try:
									subject = "<" + subject_value + ">"
									triples_map_triples.update(triple_entry) 
								except:
									subject = None

							else:
							#	field, condition = condition_separetor(triples_map.subject_map.condition)
							#	if row[field] == condition:
								try:
									subject = "<" + subject_value + ">"
									triples_map_triples.update(triple_entry) 
								except:
									subject = None 
				elif triples_map.subject_map.subject_mapping_type == "reference":
					subject_value = string_substitution_array(triples_map.subject_map.value, ".+", row, row_headers,"subject")
					subject_value = subject_value[1:-1]
					if "/" in subject_value:
						i = len(subject_value) - 1
						temp = ""
						while  0 < i:
							if subject_value[i] == "/":
								break
							else:
								temp = subject_value[i] + temp
							i -= 1
						subject_value = temp
					if triples_map.subject_map.condition == "":

						try:
							subject = "<http://example.com/base/" + subject_value + ">"
							triples_map_triples.update(triple_entry) 
						except:
							subject = None

					else:
					#	field, condition = condition_separetor(triples_map.subject_map.condition)
					#	if row[field] == condition:
						try:
							subject = "<http://example.com/base/" + subject_value + ">"
							triples_map_triples.update(triple_entry) 
						except:
							subject = None

				elif "constant" in triples_map.subject_map.subject_mapping_type:
					subject = "<" + subject_value + ">"

				else:
					if triples_map.subject_map.condition == "":

						try:
							subject =  "\"" + triples_map.subject_map.value + "\""
							triple_entry = {subject: [dictionary_maker(row)]}	
							triples_map_triples.update(triple_entry) 
						except:
							subject = None

					else:
					#	field, condition = condition_separetor(triples_map.subject_map.condition)
					#	if row[field] == condition:
						try:
							subject =  "\"" + triples_map.subject_map.value + "\""
							triple_entry = {subject: [dictionary_maker(row)]}
							triples_map_triples.update(triple_entry) 
						except:
							subject = None
		else:
			if triples_map.subject_map.subject_mapping_type == "template":
				if triples_map.subject_map.term_type is None:
					if triples_map.subject_map.condition == "":

						try:
							subject = "<" + subject_value + ">"
							triples_map_triples.update(triple_entry) 
						except:
							subject = None

					else:
					#	field, condition = condition_separetor(triples_map.subject_map.condition)
					#	if row[field] == condition:
						try:
							subject = "<" + subject_value  + ">"
							triples_map_triples.update(triple_entry) 
						except:
							subject = None
				else:
					if "IRI" in triples_map.subject_map.term_type:
						if triples_map.subject_map.condition == "":

							try:
								subject = "<http://example.com/base/" + subject_value + ">"
								triples_map_triples.update(triple_entry) 
							except:
								subject = None

						else:
						#	field, condition = condition_separetor(triples_map.subject_map.condition)
						#	if row[field] == condition:
							try:
								subject = "<http://example.com/base/" + subject_value + ">"
								triples_map_triples.update(triple_entry) 
							except:
								subject = None
						
					elif "BlankNode" in triples_map.subject_map.term_type:
						if triples_map.subject_map.condition == "":

							try:
								subject = "_:" + subject_value 
								triples_map_triples.update(triple_entry) 
							except:
								subject = None

						else:
						#	field, condition = condition_separetor(triples_map.subject_map.condition)
						#	if row[field] == condition:
							try:
								subject = "_:" + subject_value 
								triples_map_triples.update(triple_entry) 
							except:
								subject = None
					else:
						if triples_map.subject_map.condition == "":

							try:
								subject = "<" + subject_value + ">"
								triples_map_triples.update(triple_entry) 
							except:
								subject = None

						else:
						#	field, condition = condition_separetor(triples_map.subject_map.condition)
						#	if row[field] == condition:
							try:
								subject = "<" + subject_value + ">"
								triples_map_triples.update(triple_entry) 
							except:
								subject = None

			elif triples_map.subject_map.subject_mapping_type == "reference":
				if triples_map.subject_map.condition == "":
					subject_value = string_substitution_array(triples_map.subject_map.value, ".+", row, row_headers, "subject")
					subject_value = subject_value[1:-1]
					if "/" in subject_value:
						i = len(subject_value) - 1
						temp = ""
						while  0 < i:
							if subject_value[i] == "/":
								break
							else:
								temp = subject_value[i] + temp 
							i -= 1
						subject_value = temp
					try:
						subject = "<http://example.com/base/" + subject_value + ">"
						triples_map_triples.update(triple_entry) 
					except:
						subject = None

				else:
				#	field, condition = condition_separetor(triples_map.subject_map.condition)
				#	if row[field] == condition:
					try:
						subject = "<http://example.com/base/" + subject_value + ">"
						triples_map_triples.update(triple_entry) 
					except:
						subject = None

			elif "constant" in triples_map.subject_map.subject_mapping_type:
				subject = "<" + subject_value + ">"

			else:
				if triples_map.subject_map.condition == "":

					try:
						subject =  "\"" + triples_map.subject_map.value + "\""
						triple_entry = {subject: [dictionary_maker(row)]}	
						triples_map_triples.update(triple_entry) 
					except:
						subject = None

				else:
				#	field, condition = condition_separetor(triples_map.subject_map.condition)
				#	if row[field] == condition:
					try:
						subject =  "\"" + triples_map.subject_map.value + "\""
						triple_entry = {subject: [dictionary_maker(row)]}
						triples_map_triples.update(triple_entry) 
					except:
						subject = None

	else:
		if triples_map.subject_map.condition == "":

			try:
				subject = "<" + subject_value  + ">"
			except:
				subject = None

		else:
		#	field, condition = condition_separetor(triples_map.subject_map.condition)
		#	if row[field] == condition:
			try:
				subject = "<" + subject_value  + ">"
			except:
				subject = None

	if triples_map.subject_map.rdf_class is not None and subject is not None and (subject + " <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> " + "<{}> .\n".format(triples_map.subject_map.rdf_class)not in g_triples):
		if "{" in triples_map.subject_map.graph:	
			rdf_type = rdf_type[:-2] + " <" + string_substitution_array(triples_map.subject_map.graph, "{(.+?)}", row, row_headers,"subject") + "> .\n"
		else:
			rdf_type = rdf_type[:-2] + " <" + triples_map.subject_map.graph + "> .\n"
		if duplicate == "yes":
			if rdf_type not in g_triples:
				output_file_descriptor.write(rdf_type)
				csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
				g_triples.update({rdf_type : number_triple + i + 1})
				i += 1
		else:
			output_file_descriptor.write(rdf_type)
			csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
			i += 1



	for predicate_object_map in triples_map.predicate_object_maps_list:
		if predicate_object_map.predicate_map.mapping_type == "constant" or predicate_object_map.predicate_map.mapping_type == "constant shortcut":
			predicate = "<" + predicate_object_map.predicate_map.value + ">"
		elif predicate_object_map.predicate_map.mapping_type == "template":
			if predicate_object_map.predicate_map.condition != "":
				try:
					predicate = "<" + string_substitution_array(predicate_object_map.predicate_map.value, "{(.+?)}", row, row_headers, "predicate") + ">"
				except:
					predicate = None
			else:
				try:
					predicate = "<" + string_substitution_array(predicate_object_map.predicate_map.value, "{(.+?)}", row, row_headers, "predicate") + ">"
				except:
					predicate = None
		elif predicate_object_map.predicate_map.mapping_type == "reference":
			if predicate_object_map.predicate_map.condition != "":
				predicate = string_substitution_array(predicate_object_map.predicate_map.value, ".+", row, row_headers, "predicate")
		else:
			predicate = None

		if predicate_object_map.object_map.mapping_type == "constant" or predicate_object_map.object_map.mapping_type == "constant shortcut":
			if "/" in predicate_object_map.object_map.value:
				object = "<" + predicate_object_map.object_map.value + ">"
			else:
				object = "\"" + predicate_object_map.object_map.value + "\""
		elif predicate_object_map.object_map.mapping_type == "template":
			try:
				if predicate_object_map.object_map.term is None:
					object = "<" + string_substitution(predicate_object_map.object_map.value, "{(.+?)}", row, "object") + ">"
				elif "IRI" in predicate_object_map.object_map.term:
					object = "<" + string_substitution(predicate_object_map.object_map.value, "{(.+?)}", row, "object") + ">"
				else:
					object = "\"" + string_substitution(predicate_object_map.object_map.value, "{(.+?)}", row, "object") + "\""
			except TypeError:
				object = None
		elif predicate_object_map.object_map.mapping_type == "reference":
			object = string_substitution_array(predicate_object_map.object_map.value, ".+", row, row_headers, "object")
			if (predicate_object_map.object_map.language is not None) and (object is not None):
				if "spanish" in predicate_object_map.object_map.language or "es" in predicate_object_map.object_map.language :
					object += "@es"
				elif "english" in predicate_object_map.object_map.language or "en" in predicate_object_map.object_map.language :
					object += "@en"
				elif "IRI" in predicate_object_map.object_map.term:
						object = "<" + object + ">" 

		elif predicate_object_map.object_map.mapping_type == "parent triples map":
			for triples_map_element in triples_map_list:
				if triples_map_element.triples_map_id == predicate_object_map.object_map.value:
					if (triples_map_element.data_source != triples_map.data_source) or (triples_map_element.tablename != triples_map.tablename):
						if triples_map_element.triples_map_id + "_" + predicate_object_map.object_map.child not in join_table:
							if str(triples_map_element.file_format).lower() == "csv" or triples_map_element.file_format == "JSONPath":
								with open(str(triples_map_element.data_source), "r") as input_file_descriptor:
									if str(triples_map_element.file_format).lower() == "csv":
										data = csv.DictReader(input_file_descriptor, delimiter=delimiter)
										hash_maker(data, triples_map_element, predicate_object_map.object_map)
									else:
										data = json.load(input_file_descriptor)
										hash_maker(data[list(data.keys())[0]], triples_map_element, predicate_object_map.object_map)								
							else:
								database, query_list = translate_sql(triples_map_element)
								db = connector.connect(host="localhost", port=3306, user="root", password="06012009mj")
								cursor = db.cursor()
								if database == None:
									cursor.execute("use " + database)
								else:
									cursor.execute("use test")
								for query in query_list:
									cursor.execute(query)
									data = cursor
								hash_maker_array(cursor, triples_map_element, predicate_object_map.object_map)
						jt = join_table[triples_map_element.triples_map_id + "_" + predicate_object_map.object_map.child[0]]
						if row[row_headers.index(predicate_object_map.object_map.child[0])] is not None:
							object_list = jt[row[row_headers.index(predicate_object_map.object_map.child[0])]]
						object = None
					else:
						try:
							database, query_list = translate_sql(triples_map)
							database2, query_list_origin = translate_sql(triples_map_element)
							db = connector.connect(host = "localhost", port = 3306, user = "root", password = "06012009mj")
							cursor = db.cursor()
							if database == None:
								cursor.execute("use " + database)
							else:
								cursor.execute("use test")
							for query in query_list:
								for q in query_list_origin:
									query_1 = q.split("FROM")
									query_2 = query.split("SELECT")[1].split("FROM")[0]
									query_new = query_1[0] + " , " + query_2 + " FROM " + query_1[1]
									cursor.execute(query_new)
									r_h=[x[0] for x in cursor.description]
									for r in cursor:
										s = string_substitution_array(triples_map.subject_map.value, "{(.+?)}", r, r_h, "subject")
										if subject_value == s:
											object = "<" + string_substitution_array(triples_map_element.subject_map.value, "{(.+?)}", r, r_h, "object") + ">"
						except TypeError:
							object = None
					break
				else:
					continue
		else:
			object = None

		if object is not None and predicate_object_map.object_map.datatype is not None:
			object += "^^<{}>".format(predicate_object_map.object_map.datatype)

		if predicate is not None and object is not None and subject is not None:
			triple = subject + " " + predicate + " " + object + ".\n"
			if duplicate == "yes":
				if triples_map.subject_map.graph is not None:
					if "{" in triples_map.subject_map.graph:
						triple = triple[:-2] + " <" + string_substitution_array(triples_map.subject_map.graph, "{(.+?)}", row, row_headers,"subject") + ">.\n"
					else:
						triple = triple[:-2] + " <" + triples_map.subject_map.graph + ">.\n"
				if triple not in g_triples:
					output_file_descriptor.write(triple)
					csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
					g_triples.update({triple : number_triple})
					i += 1
			else:
				output_file_descriptor.write(triple)
				csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
				i += 1
		elif predicate is not None and subject is not None and object_list:
			for obj in object_list:
				triple = subject + " " + predicate + " " + obj + ".\n"
				if triples_map.subject_map.graph is not None:
					if "{" in triples_map.subject_map.graph:
						triple = triple[:-2] + " <" + string_substitution_array(triples_map.subject_map.graph, "{(.+?)}", row, row_headers,"subject") + ">.\n"
					else:
						triple = triple[:-2] + " <" + triples_map.subject_map.graph + ">.\n"

				if duplicate == "yes":
					if triple not in g_triples:
						output_file_descriptor.write(triple)
						csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
						g_triples.update({triple : number_triple})
						i += 1
				else:
					output_file_descriptor.write(triple)
					csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
					i += 1
			object_list = []
		else:
			continue
	return i

def semantify_postgres(row, row_headers, triples_map, triples_map_list, output_file_descriptor, csv_file, dataset_name):

	"""
	(Private function, not accessible from outside this package)

	Takes a triples-map rule and applies it to each one of the rows of its CSV data
	source

	Parameters
	----------
	triples_map : TriplesMap object
		Mapping rule consisting of a logical source, a subject-map and several predicateObjectMaps
		(refer to the TriplesMap.py file in the triplesmap folder)
	triples_map_list : list of TriplesMap objects
		List of triples-maps parsed from current mapping being used for the semantification of a
		dataset (mainly used to perform rr:joinCondition mappings)
	delimiter : string
		Delimiter value for the CSV or TSV file ("\s" and "\t" respectively)
	output_file_descriptor : file object 
		Descriptor to the output file (refer to the Python 3 documentation)

	Returns
	-------
	An .nt file per each dataset mentioned in the configuration file semantified.
	If the duplicates are asked to be removed in main memory, also returns a -min.nt
	file with the triples sorted and with the duplicates removed.
	"""
	triples_map_triples = {}
	generated_triples = {}
	object_list = []
	subject_value = string_substitution_array(triples_map.subject_map.value, "{(.+?)}", row, row_headers, "subject")
	i = 0
	if duplicate == "yes":
		triple_entry = {subject_value: dictionary_maker_array(row, row_headers)}
		if subject_value in triples_map_triples:
			if shared_items(triples_map_triples[subject_value], triple_entry) == len(triples_map_triples[subject_value]):
				subject = None
			else:
				if triples_map.subject_map.subject_mapping_type == "template":
					if triples_map.subject_map.term_type is None:
						if triples_map.subject_map.condition == "":

							try:
								subject = "<" + subject_value + ">"
								triples_map_triples[subject_value].append(dictionary_maker(row)) 
							except:
								subject = None

						else:
						#	field, condition = condition_separetor(triples_map.subject_map.condition)
						#	if row[field] == condition:
							try:
								subject = "<" + subject_value  + ">"
								triples_map_triples[subject_value].append(dictionary_maker(row)) 
							except:
								subject = None 
					else:
						if "IRI" in triples_map.subject_map.term_type:
							if triples_map.subject_map.condition == "":

								try:
									subject = "<http://example.com/base/" + subject_value + ">"
									triples_map_triples[subject_value].append(dictionary_maker(row)) 
								except:
									subject = None

							else:
							#	field, condition = condition_separetor(triples_map.subject_map.condition)
							#	if row[field] == condition:
								try:
									subject = "<http://example.com/base/" + subject_value + ">"
									triples_map_triples[subject_value].append(dictionary_maker(row)) 
								except:
									subject = None 

						elif "BlankNode" in triples_map.subject_map.term_type:
							if triples_map.subject_map.condition == "":

								try:
									subject = "_:" + subject_value
									triples_map_triples[subject_value].append(dictionary_maker(row)) 
								except:
									subject = None

							else:
							#	field, condition = condition_separetor(triples_map.subject_map.condition)
							#	if row[field] == condition:
								try:
									subject = "_:" + subject_value  
									triples_map_triples[subject_value].append(dictionary_maker(row)) 
								except:
									subject = None
									
						else:
							if triples_map.subject_map.condition == "":

								try:
									subject = "<" + subject_value + ">"
									triples_map_triples.update(triple_entry) 
								except:
									subject = None

							else:
							#	field, condition = condition_separetor(triples_map.subject_map.condition)
							#	if row[field] == condition:
								try:
									subject = "<" + subject_value + ">"
									triples_map_triples.update(triple_entry) 
								except:
									subject = None 
				elif triples_map.subject_map.subject_mapping_type == "reference":
					subject_value = string_substitution_array(triples_map.subject_map.value, ".+", row, row_headers,"subject")
					subject_value = subject_value[1:-1]
					if "/" in subject_value:
						i = len(subject_value) - 1
						temp = ""
						while  0 < i:
							if subject_value[i] == "/":
								break
							else:
								temp = subject_value[i] + temp
							i -= 1
						subject_value = temp
					if triples_map.subject_map.condition == "":

						try:
							subject = "<http://example.com/base/" + subject_value + ">"
							triples_map_triples.update(triple_entry) 
						except:
							subject = None

					else:
					#	field, condition = condition_separetor(triples_map.subject_map.condition)
					#	if row[field] == condition:
						try:
							subject = "<http://example.com/base/" + subject_value + ">"
							triples_map_triples.update(triple_entry) 
						except:
							subject = None
				
				elif "constant" in triples_map.subject_map.subject_mapping_type:
					subject = "<" + subject_value + ">"

				else:
					if triples_map.subject_map.condition == "":

						try:
							subject =  "\"" + triples_map.subject_map.value + "\""
							triple_entry = {subject: [dictionary_maker(row)]}	
							triples_map_triples.update(triple_entry) 
						except:
							subject = None

					else:
					#	field, condition = condition_separetor(triples_map.subject_map.condition)
					#	if row[field] == condition:
						try:
							subject =  "\"" + triples_map.subject_map.value + "\""
							triple_entry = {subject: [dictionary_maker(row)]}
							triples_map_triples.update(triple_entry) 
						except:
							subject = None
		else:
			if triples_map.subject_map.subject_mapping_type == "template":
				if triples_map.subject_map.term_type is None:
					if triples_map.subject_map.condition == "":

						try:
							subject = "<" + subject_value + ">"
							triples_map_triples.update(triple_entry) 
						except:
							subject = None

					else:
					#	field, condition = condition_separetor(triples_map.subject_map.condition)
					#	if row[field] == condition:
						try:
							subject = "<" + subject_value  + ">"
							triples_map_triples.update(triple_entry) 
						except:
							subject = None
				else:
					if "IRI" in triples_map.subject_map.term_type:
						if triples_map.subject_map.condition == "":

							try:
								subject = "<http://example.com/base/" + subject_value + ">"
								triples_map_triples.update(triple_entry) 
							except:
								subject = None

						else:
						#	field, condition = condition_separetor(triples_map.subject_map.condition)
						#	if row[field] == condition:
							try:
								subject = "<http://example.com/base/" + subject_value + ">"
								triples_map_triples.update(triple_entry) 
							except:
								subject = None
						
					elif "BlankNode" in triples_map.subject_map.term_type:
						if triples_map.subject_map.condition == "":

							try:
								subject = "_:" + subject_value 
								triples_map_triples.update(triple_entry) 
							except:
								subject = None

						else:
						#	field, condition = condition_separetor(triples_map.subject_map.condition)
						#	if row[field] == condition:
							try:
								subject = "_:" + subject_value 
								triples_map_triples.update(triple_entry) 
							except:
								subject = None
					else:
						if triples_map.subject_map.condition == "":

							try:
								subject = "<" + subject_value + ">"
								triples_map_triples.update(triple_entry) 
							except:
								subject = None

						else:
						#	field, condition = condition_separetor(triples_map.subject_map.condition)
						#	if row[field] == condition:
							try:
								subject = "<" + subject_value + ">"
								triples_map_triples.update(triple_entry) 
							except:
								subject = None

			elif triples_map.subject_map.subject_mapping_type == "reference":
				if triples_map.subject_map.condition == "":
					subject_value = string_substitution_array(triples_map.subject_map.value, ".+", row, row_headers,"subject")
					subject_value = subject_value[1:-1]
					if "/" in subject_value:
						i = len(subject_value) - 1
						temp = ""
						while  0 < i:
							if subject_value[i] == "/":
								break
							else:
								temp = subject_value[i] + temp 
							i -= 1
						subject_value = temp
					try:
						subject = "<http://example.com/base/" + subject_value + ">"
						triples_map_triples.update(triple_entry) 
					except:
						subject = None

				else:
				#	field, condition = condition_separetor(triples_map.subject_map.condition)
				#	if row[field] == condition:
					try:
						subject = "<http://example.com/base/" + subject_value + ">"
						triples_map_triples.update(triple_entry) 
					except:
						subject = None
			
			elif "constant" in triples_map.subject_map.subject_mapping_type:
				subject = "<" + subject_value + ">"

			else:
				if triples_map.subject_map.condition == "":

					try:
						subject =  "\"" + triples_map.subject_map.value + "\""
						triple_entry = {subject: [dictionary_maker(row)]}	
						triples_map_triples.update(triple_entry) 
					except:
						subject = None

				else:
				#	field, condition = condition_separetor(triples_map.subject_map.condition)
				#	if row[field] == condition:
					try:
						subject =  "\"" + triples_map.subject_map.value + "\""
						triple_entry = {subject: [dictionary_maker(row)]}
						triples_map_triples.update(triple_entry) 
					except:
						subject = None

	else:
		if triples_map.subject_map.condition == "":

			try:
				subject = "<" + subject_value  + ">"
			except:
				subject = None

		else:
		#	field, condition = condition_separetor(triples_map.subject_map.condition)
		#	if row[field] == condition:
			try:
				subject = "<" + subject_value  + ">"
			except:
				subject = None

	if triples_map.subject_map.rdf_class is not None and subject is not None and (subject + " <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> " + "<{}> .\n".format(triples_map.subject_map.rdf_class)not in g_triples):
		if "{" in triples_map.subject_map.graph:	
			rdf_type = rdf_type[:-2] + " <" + string_substitution_array(triples_map.subject_map.graph, "{(.+?)}", row, row_headers,"subject") + "> .\n"
		else:
			rdf_type = rdf_type[:-2] + " <" + triples_map.subject_map.graph + "> .\n"
		if duplicate == "yes":
			if rdf_type not in g_triples:
				output_file_descriptor.write(rdf_type)
				csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
				g_triples.update({rdf_type : number_triple + i + 1})
				i += 1
		else:
			output_file_descriptor.write(rdf_type)
			csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
			i += 1



	for predicate_object_map in triples_map.predicate_object_maps_list:
		if predicate_object_map.predicate_map.mapping_type == "constant" or predicate_object_map.predicate_map.mapping_type == "constant shortcut":
			predicate = "<" + predicate_object_map.predicate_map.value + ">"
		elif predicate_object_map.predicate_map.mapping_type == "template":
			if predicate_object_map.predicate_map.condition != "":
				try:
					predicate = "<" + string_substitution_postgres(predicate_object_map.predicate_map.value, "{(.+?)}", row, row_headers, "predicate") + ">"
				except:
					predicate = None
			else:
				try:
					predicate = "<" + string_substitution_postgres(predicate_object_map.predicate_map.value, "{(.+?)}", row, row_headers, "predicate") + ">"
				except:
					predicate = None
		elif predicate_object_map.predicate_map.mapping_type == "reference":
				if predicate_object_map.predicate_map.condition != "":
					predicate = string_substitution_postgres(predicate_object_map.predicate_map.value, ".+", row, row_headers, "predicate")
		else:
			predicate = None

		if predicate_object_map.object_map.mapping_type == "constant" or predicate_object_map.object_map.mapping_type == "constant shortcut":
			if "/" in predicate_object_map.object_map.value:
				object = "<" + predicate_object_map.object_map.value + ">"
			else:
				object = "\"" + predicate_object_map.object_map.value + "\""
		elif predicate_object_map.object_map.mapping_type == "template":
			try:
				if predicate_object_map.object_map.term is None:
					object = "<" + string_substitution(predicate_object_map.object_map.value, "{(.+?)}", row, "object") + ">"
				elif "IRI" in predicate_object_map.object_map.term:
					object = "<" + string_substitution(predicate_object_map.object_map.value, "{(.+?)}", row, "object") + ">"
				else:
					object = "\"" + string_substitution(predicate_object_map.object_map.value, "{(.+?)}", row, "object") + "\""
			except TypeError:
				object = None
		elif predicate_object_map.object_map.mapping_type == "reference":
			object = string_substitution_array(predicate_object_map.object_map.value, ".+", row, row_headers, "object")
			if (predicate_object_map.object_map.language is not None) and (object is not None):
				if "spanish" in predicate_object_map.object_map.language or "es" in predicate_object_map.object_map.language :
					object += "@es"
				elif "english" in predicate_object_map.object_map.language or "en" in predicate_object_map.object_map.language :
					object += "@en"
				elif "IRI" in predicate_object_map.object_map.term:
						object = "<" + object + ">" 
		elif predicate_object_map.object_map.mapping_type == "parent triples map":
			for triples_map_element in triples_map_list:
				if triples_map_element.triples_map_id == predicate_object_map.object_map.value:
					if (triples_map_element.data_source != triples_map.data_source) or (triples_map_element.tablename != triples_map.tablename):
						if triples_map_element.triples_map_id + "_" + predicate_object_map.object_map.child not in join_table:
							if str(triples_map_element.file_format).lower() == "csv" or triples_map_element.file_format == "JSONPath":
								with open(str(triples_map_element.data_source), "r") as input_file_descriptor:
									if str(triples_map_element.file_format).lower() == "csv":
										data = csv.DictReader(input_file_descriptor, delimiter=delimiter)
										hash_maker(data, triples_map_element, predicate_object_map.object_map)
									else:
										data = json.load(input_file_descriptor)
										hash_maker(data[list(data.keys())[0]], triples_map_element, predicate_object_map.object_map)								
							else:
								database, query_list = translate_postgressql(triples_map_element)
								db = psycopg2.connect( host="localhost", user="postgres", password="postgres", dbname="" )
								cursor = db.cursor()
								for query in query_list:
									cursor.execute(query)
									data = cursor
								hash_maker_array(cursor, triples_map_element, predicate_object_map.object_map)
						jt = join_table[triples_map_element.triples_map_id + "_" + predicate_object_map.object_map.child[0]]
						if row[row_headers.index(predicate_object_map.object_map.child[0])] is not None:
							object_list = jt[row[row_headers.index(predicate_object_map.object_map.child[0])]]
						object = None
					else:
						try:
							database, query_list = translate_postgressql(triples_map)
							database2, query_list_origin = translate_postgressql(triples_map_element)
							db = psycopg2.connect( host="localhost", user="postgres", password="postgres", dbname="" )
							cursor = db.cursor()
							for query in query_list:
								for q in query_list_origin:
									query_1 = q.split("FROM")
									query_2 = query.split("SELECT")[1].split("FROM")[0]
									query_new = query_1[0] + ", " + query_2 + " FROM " + query_1[1]
									cursor.execute(query_new)
									r_h=[x[0] for x in cursor.description]
									for r in cursor:
										s = string_substitution_postgres(triples_map.subject_map.value, "{(.+?)}", r, r_h, "subject")
										if subject_value == s:
											object = "<" + string_substitution_postgres(triples_map_element.subject_map.value, "{(.+?)}", r, r_h, "object") + ">"
						except TypeError:
							object = None
					break
				else:
					continue
		else:
			object = None

		if object is not None and predicate_object_map.object_map.datatype is not None:
			object += "^^<{}>".format(predicate_object_map.object_map.datatype)

		if predicate is not None and object is not None and subject is not None:
			triple = subject + " " + predicate + " " + object + ".\n"
			if triples_map.subject_map.graph is not None:
				if "{" in triples_map.subject_map.graph:
					triple = triple[:-2] + " <" + string_substitution_array(triples_map.subject_map.graph, "{(.+?)}", row, row_headers,"subject") + ">.\n"
				else:
					triple = triple[:-2] + " <" + triples_map.subject_map.graph + ">.\n"
			if duplicate == "yes":
				if triple not in g_triples:
					output_file_descriptor.write(triple)
					csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
					g_triples.update({triple : number_triple})
					i += 1
			else:
				output_file_descriptor.write(triple)
				csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
				i += 1
		elif predicate is not None and subject is not None and object_list:
			for obj in object_list:
				if "IRI" in predicate_object_map.object_map.term:
					triple = subject + " " + predicate + " <" + obj[1:-1] + ">.\n"
				else:
					triple = subject + " " + predicate + " " + obj + ".\n"
				if triples_map.subject_map.graph is not None:
					if "{" in triples_map.subject_map.graph:
						triple = triple[:-2] + " <" + string_substitution_array(triples_map.subject_map.graph, "{(.+?)}", row, row_headers,"subject") + ">.\n"
					else:
						triple = triple[:-2] + " <" + triples_map.subject_map.graph + ">.\n"
				if duplicate == "yes":
					if triple not in g_triples:
						output_file_descriptor.write(triple)
						csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
						g_triples.update({triple : number_triple})
						i += 1
				else:
					output_file_descriptor.write(triple)
					csv_file.writerow([dataset_name, number_triple + i + 1, time.time()-start_time])
					i += 1
			object_list = []
		else:
			continue
	return i

def translate_sql(triples_map):

	query_list = []
	
	
	proyections = []

		
	if "{" in triples_map.subject_map.value:
		subject = triples_map.subject_map.value
		count = count_characters(subject)
		if (count == 1) and (subject.split("{")[1].split("}")[0] not in proyections):
			subject = subject.split("{")[1].split("}")[0]
			if "[" in subject:
				subject = subject.split("[")[0]
			proyections.append(subject)
		elif count > 1:
			subject_list = subject.split("{")
			for s in subject_list:
				if "}" in s:
					subject = s.split("}")[0]
					if "[" in subject:
						subject = subject.split("[")
					if subject not in proyections:
						proyections.append(subject)

	for po in triples_map.predicate_object_maps_list:
		if "{" in po.object_map.value:
			count = count_characters(po.object_map.value)
			if 0 < count <= 1 :
				predicate = po.object_map.value.split("{")[1].split("}")[0]
				if "[" in predicate:
					predicate = predicate.split("[")[0]
				if predicate not in proyections:
					proyections.append(predicate)

			elif 1 < count:
				predicate = po.object_map.value.split("{")
				for po_e in predicate:
					if "}" in po_e:
						pre = po_e.split("}")[0]
						if "[" in pre:
							pre = pre.split("[")
						if pre not in proyections:
							proyections.append(pre)
		elif "#" in po.object_map.value:
			pass
		elif "/" in po.object_map.value:
			pass
		else:
			predicate = po.object_map.value 
			if "[" in predicate:
				predicate = predicate.split("[")[0]
			if predicate not in proyections:
					proyections.append(predicate)
		if po.object_map.child != None:
			if po.object_map.child not in proyections:
					proyections.append(po.object_map.child)

	temp_query = "SELECT "
	for p in proyections:
		if p is not "None":
			if p == proyections[len(proyections)-1]:
				temp_query += p
			else:
				temp_query += p + ", " 
		else:
			temp_query = temp_query[:-2] 
	if triples_map.tablename != "None":
		temp_query = temp_query + " FROM " + triples_map.tablename + ";"
	else:
		temp_query = temp_query + " FROM " + triples_map.data_source + ";"
	query_list.append(temp_query)

	return triples_map.iterator, query_list


def translate_postgressql(triples_map):

	query_list = []
	
	
	proyections = []

		
	if "{" in triples_map.subject_map.value:
		subject = triples_map.subject_map.value
		count = count_characters(subject)
		if (count == 1) and (subject.split("{")[1].split("}")[0] not in proyections):
			subject = subject.split("{")[1].split("}")[0]
			if "[" in subject:
				subject = subject.split("[")[0]
			proyections.append(subject)
		elif count > 1:
			subject_list = subject.split("{")
			for s in subject_list:
				if "}" in s:
					subject = s.split("}")[0]
					if "[" in subject:
						subject = subject.split("[")
					if subject not in proyections:
						proyections.append(subject)

	for po in triples_map.predicate_object_maps_list:
		if "{" in po.object_map.value:
			count = count_characters(po.object_map.value)
			if 0 < count <= 1 :
				predicate = po.object_map.value.split("{")[1].split("}")[0]
				if "[" in predicate:
					predicate = predicate.split("[")[0]
				if predicate not in proyections:
					proyections.append(predicate)

			elif 1 < count:
				predicate = po.object_map.value.split("{")
				for po_e in predicate:
					if "}" in po_e:
						pre = po_e.split("}")[0]
						if "[" in pre:
							pre = pre.split("[")
						if pre not in proyections:
							proyections.append(pre)
		elif "#" in po.object_map.value:
			pass
		elif "/" in po.object_map.value:
			pass
		else:
			predicate = po.object_map.value 
			if "[" in predicate:
				predicate = predicate.split("[")[0]
			if predicate not in proyections:
					proyections.append(predicate)
		if po.object_map.child != None:
			if po.object_map.child not in proyections:
					proyections.append(po.object_map.child)

	temp_query = "SELECT "
	for p in proyections:
		if p is not "None":
			if p == proyections[len(proyections)-1]:
				temp_query += "\"" + p + "\""
			else:
				temp_query += "\"" + p + "\", " 
		else:
			temp_query = temp_query[:-2] 
	if triples_map.tablename != "None":
		temp_query = temp_query + " FROM " + triples_map.tablename + ";"
	else:
		temp_query = temp_query + " FROM " + triples_map.data_source + ";"
	query_list.append(temp_query)

	return triples_map.iterator, query_list

def semantify(config_path):

	"""
	Takes the configuration file path and sets the necessary variables to perform the
	semantification of each dataset presented in said file.

	Given a TTL/N3 mapping file expressing the correspondance rules between the raw
	data and the desired semantified data, the main function performs all the
	necessary operations to do this transformation

	Parameters
	----------
	config_path : string
		Path to the configuration file

	Returns
	-------
	An .nt file per each dataset mentioned in the configuration file semantified.
	If the duplicates are asked to be removed in main memory, also returns a -min.nt
	file with the triples sorted and with the duplicates removed.

	(No variable returned)
	
	"""

	config = ConfigParser(interpolation=ExtendedInterpolation())
	config.read(config_path)

	global duplicate
	duplicate = config["datasets"]["remove_duplicate"]

	enrichment = config["datasets"]["enrichment"]

	if not os.path.exists(config["datasets"]["output_folder"]):
			os.mkdir(config["datasets"]["output_folder"])

	global start_time
	if config["datasets"]["all_in_one_file"] == "no":
		
		start_time = time.time()

		with open(config["datasets"]["output_folder"] + "/" +  config["datasets"]["name"] + "_datasets_stats.csv", 'w') as myfile:
			wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
			wr.writerow(["Dataset", "Number of the triple", "Time"])

			with ThreadPoolExecutor(max_workers=10) as executor:
				for dataset_number in range(int(config["datasets"]["number_of_datasets"])):
					dataset_i = "dataset" + str(int(dataset_number) + 1)
					triples_map_list = mapping_parser(config[dataset_i]["mapping"])
					output_file = config["datasets"]["output_folder"] + "/" + config[dataset_i]["name"] + ".nt"

					print("Semantifying {}...".format(config[dataset_i]["name"]))
					
					with open(output_file, "w") as output_file_descriptor:
						for triples_map in triples_map_list:
							global number_triple
							if enrichment == "yes":
								if str(triples_map.file_format).lower() == "csv" and triples_map.query == "None":
									with open(str(triples_map.data_source), "r") as input_file_descriptor:
										data = csv.DictReader(input_file_descriptor, delimiter=',')
										number_triple += executor.submit(semantify_file, triples_map, triples_map_list, ",", output_file_descriptor, wr, config[dataset_i]["name"], data).result()
								elif triples_map.file_format == "JSONPath" and triples_map.query == "None":
									with open(str(triples_map.data_source), "r") as input_file_descriptor:
										data = json.load(input_file_descriptor)
										if len(data) < 2:
											number_triple += executor.submit(semantify_file, triples_map, triples_map_list, ",",output_file_descriptor, wr, config[dataset_i]["name"], data[list(data.keys())[0]]).result()
										else:
											number_triple += executor.submit(semantify_json, triples_map, triples_map_list, ",",output_file_descriptor, wr, config[dataset_i]["name"], data).result()
								elif triples_map.file_format == "XPath":
									number_triple += executor.submit(semantify_xml, triples_map, triples_map_list, output_file_descriptor, wr, config[dataset_i]["name"]).result()
								elif config["datasets"]["dbType"] == "mysql":
									user, password, port, host = config[dataset_i]["user"], config[dataset_i]["password"], int(config[dataset_i]["port"]), config[dataset_i]["host"]
									database, query_list = translate_sql(triples_map)
									db = connector.connect(host = host, port = port, user = user, password = password)
									cursor = db.cursor()
									if database != "None":
										cursor.execute("use " + database)
									else:
										cursor.execute("use test")
									if triples_map.query == "None":	
										for query in query_list:
											cursor.execute(query)
											row_headers=[x[0] for x in cursor.description]
											for row in cursor:
												number_triple += executor.submit(semantify_mysql, row, row_headers, triples_map, triples_map_list, output_file_descriptor, wr, config[dataset_i]["name"]).result()
									else:
										cursor.execute(triples_map.query)
										row_headers=[x[0] for x in cursor.description]
										for row in cursor:
											number_triple += executor.submit(semantify_mysql, row, row_headers, triples_map, triples_map_list, output_file_descriptor, wr, config[dataset_i]["name"]).result()
								elif config["datasets"]["dbType"] == "postgres":
									
									user, password, db, host = config[dataset_i]["user"], config[dataset_i]["password"], config[dataset_i]["db"], config[dataset_i]["host"]	
									database, query_list = translate_sql(triples_map)
									db = psycopg2.connect( host=host, user=user, password=password, dbname=db )
									cursor = db.cursor()
									if triples_map.query == "None":	
										for query in query_list:
											cursor.execute(query)
											row_headers=[x[0] for x in cursor.description]
											for row in cursor:
												number_triple += executor.submit(semantify_postgres, row, row_headers, triples_map, triples_map_list, output_file_descriptor, wr, config[dataset_i]["name"]).result()
									else:
										cursor.execute(triples_map.query)
										row_headers=[x[0] for x in cursor.description]
										for row in cursor:
											number_triple += executor.submit(semantify_postgres, row, row_headers, triples_map, triples_map_list, output_file_descriptor, wr, config[dataset_i]["name"]).result()					
								else:
									print("Invalid reference formulation or format")
									print("Aborting...")
									sys.exit(1)
							else:
								if str(triples_map.file_format).lower() == "csv" and triples_map.query == "None":
									with open(str(triples_map.data_source), "r") as input_file_descriptor:
										data = csv.DictReader(input_file_descriptor, delimiter=',')
										number_triple += executor.submit(semantify_file_array, triples_map, triples_map_list, ",", output_file_descriptor, wr, config[dataset_i]["name"], data).result()
								elif triples_map.file_format == "JSONPath" and triples_map.query == "None":
									with open(str(triples_map.data_source), "r") as input_file_descriptor:
										data = json.load(input_file_descriptor)
										number_triple += executor.submit(semantify_file_array, triples_map, triples_map_list, output_file_descriptor, wr, config[dataset_i]["name"], data).result()
								elif triples_map.tablename != "None" or triples_map.iterator != "None":
									user, password, port, host = config[dataset_i]["user"], config[dataset_i]["password"], int(config[dataset_i]["port"]), config[dataset_i]["host"]
									
									db = connector.connect(host = host, port = port, user = user, password = password)
									cursor = db.cursor()
									database, query_list = translate_sql(triples_map)
									cursor.execute("use " + database)
									for query in query_list:
										cursor.execute(query)
										row_headers=[x[0] for x in cursor.description]
										for row in cursor:
											number_triple += executor.submit(semantify_mysql, row, row_headers, triples_map, triples_map_list, output_file_descriptor, wr, config[dataset_i]["name"]).result()
								elif triples_map.file_format == "XPath":
									number_triple += executor.submit(semantify_xml, triples_map, triples_map_list, output_file_descriptor, wr, config[dataset_i]["name"]).result()		
								else:
									print("Invalid reference formulation or format")
									print("Aborting...")
									sys.exit(1)

					print("Successfully semantified {}\n".format(config[dataset_i]["name"]))


		with open(config["datasets"]["output_folder"] + "/stats.csv", 'w') as myfile:
			wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
			wr.writerow(["Number of triples", "Time"])
			wr.writerow([number_triple, time.time()-start_time])

	else:
		output_file = config["datasets"]["output_folder"] + "/" + config["datasets"]["name"] + ".nt" 
		print("Semantifying {}.{}...".format(config["datasets"]["name"]))

		start_time = time.time()
		with open(output_file, "w") as output_file_descriptor:
			with open(config["datasets"]["output_folder"] + "/" + "datasets_stats.csv", 'w') as myfile:
				wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
				wr.writerow(["Dataset", "Number of the triple", "Time"])
				with ThreadPoolExecutor(max_workers=10) as executor:
					for dataset_number in range(int(config["datasets"]["number_of_datasets"])):
						dataset_i = "dataset" + str(int(dataset_number) + 1)
						triples_map_list = mapping_parser(config[dataset_i]["mapping"])

						for triples_map in triples_map_list:
							#global number_triple
							if str(triples_map.file_format).lower() == "csv" and config[dataset_i]["format"].lower() == "csv":
								with open(str(triples_map.data_source), "r") as input_file_descriptor:
									data = csv.DictReader(input_file_descriptor, delimiter=",")
									number_triple += executor.submit(semantify_file, triples_map, triples_map_list, ",", output_file_descriptor, wr, config[dataset_i]["name"], data).results()
							elif triples_map.file_format == "JSONPath":
								with open(str(triples_map.data_source), "r") as input_file_descriptor:
									data = json.load(input_file_descriptor)
									number_triple += executor.submit(semantify_file, triples_map, triples_map_list, output_file_descriptor, wr, config[dataset_i]["name"], data[0]).results()
							elif triples_map.file_format == "SQL" or triples_map.file_format == "TSV":
								database, query_list = translate_sql(triples_map)
								#global user, password, port, host
								user, password, port, host = config[dataset_i]["user"], config[dataset_i]["password"], int(config[dataset_i]["port"]), config[dataset_i]["host"]
								db = connector.connect(host=host, port=port, user=user, password=password)
								cursor = db.cursor()
								cursor.execute("use " + database)
								for query in query_list:
									cursor.execute(query)
									row_headers=[x[0] for x in cursor.description]
									for row in cursor:
										number_triple += executor.submit(semantify_mysql, row, row_headers, triples_map, triples_map_list, output_file_descriptor, wr,config[dataset_i]["name"])
							else:
								print("Invalid reference formulation or format")
								print("Aborting...")
								sys.exit(1)

		with open(config["datasets"]["output_folder"] + "stats.csv", 'w') as myfile:
			wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
			wr.writerow(["Number of triples", "Time"])
			wr.writerow([number_triple, time.time()-start_time])


		print("Successfully semantified {}.{}\n".format(config[dataset_i]["name"]))

		

def main():

	"""
	Function executed when the current file is executed as a script, instead of being
	executed as a Python package in another script.

	When executing the current file as a script in the terminal, the following flags
	are accepted:

	-h (python3 semantify.py -h): prompts the correct use of semantify.py as a script
	-c (python3 semantify.py -c <config_file>): executes the program as a script with
		with the <config_file> parameter as the path to the configuration file to be
		used
	--config_file (python3 semantify.py --config_file <config_file>): same behaviour
		as -c flag

	Parameters
	----------
	Nothing

	Returns
	-------
	Nothing

	"""

	argv = sys.argv[1:]
	try:
		opts, args = getopt.getopt(argv, 'hc:', 'config_file=')
	except getopt.GetoptError:
		print('python3 semantify.py -c <config_file>')
		sys.exit(1)
	for opt, arg in opts:
		if opt == '-h':
			print('python3 semantify.py -c <config_file>')
			sys.exit()
		elif opt == '-c' or opt == '--config_file':
			config_path = arg

	semantify(config_path)

if __name__ == "__main__":
	main()

"""
According to the meeting held on 11.04.2018, semantifying json files is not a top priority right
now, thus the reimplementation of following functions remain largely undocumented and unfinished.

def json_generator(file_descriptor, iterator):
	if len(iterator) != 0:
		if "[*]" not in iterator[0] and iterator[0] != "$":
			yield from json_generator(file_descriptor[iterator[0]], iterator[1:])
		elif "[*]" not in iterator[0] and iterator[0] == "$":
			yield from json_generator(file, iterator[1:])
		elif "[*]" in iterator[0] and "$" not in iterator[0]:
			file_array = file_descriptor[iterator[0].replace("[*]","")]
			for array_elem in file_array:
				yield from json_generator(array_elem, iterator[1:])
		elif iterator[0] == "$[*]":
			for array_elem in file_descriptor:
				yield from json_generator(array_elem, iterator[1:])
	else:
		yield file_descriptor


"""
