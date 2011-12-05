# -*- coding: utf-8 -*-
#
# Copyright (c) 2011-2011, RMIT e-Research Office
#   (RMIT University, Australia)
# Copyright (c) 2010-2011, Monash e-Research Centre
#   (Monash University, Australia)
# All rights reserved.
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    *  Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#    *  Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#    *  Neither the name of the VeRSI, the VeRSI Consortium members, nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE REGENTS AND CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

"""
metadata.py

.. moduleauthor:: Ian Thomas <Ian.Edward.Thomas@rmit.edu.au>

"""
from os import path
import re
import itertools
import logging

from django.conf import settings
from django.core.management.base import BaseCommand

from tardis.tardis_portal.models import Dataset_File
from tardis.tardis_portal.models import Dataset
from tardis.tardis_portal.models import DatafileParameter
from tardis.tardis_portal.models import DatafileParameterSet
from tardis.tardis_portal.models import ParameterName
from tardis.tardis_portal.models import Schema
from tardis.tardis_portal.models import DatasetParameter
from tardis.tardis_portal.models import DatasetParameterSet
from tardis.tardis_portal.models import Experiment

logger = logging.getLogger(__name__)


number = "[+-]?((\d+)(\.\d*)?)|(\d+\.\d+)([eE][+-]?[0-9]+)?"
rulesets = {('http://tardis.edu.au/schemas/vasp/1','vasp 1.0'):
                (
                 ('kpoint_grid',("KPOINTS[_0-9]*",),
                 "get_file_line(context,'KPOINTS[_0-9]*',-3)"),
                 
                 ('kpoint_grid_offset',("KPOINTS[_0-9]*",),
                 "get_file_line(context,'KPOINTS[_0-9]*',-2)"),
                 
                 # TODO: remove number as can cause bad matches 
                 ('ENCUT',("OUTCAR[_0-9]*",),
                 "get_file_regex(context,'OUTCAR[_0-9]*','\s+ENCUT\s*=\s*(?P<value>%s)\s+(?P<unit>eV)',False)" % number),
                 
                 ('NIONS',("OUTCAR[_0-9]*",),
                 "get_file_regex(context,'OUTCAR[_0-9]*','\s+NIONS\s*\=\s*(?P<value>%s)(?P<unit>)',False)" % number),
                 
                 ('NELECT',("OUTCAR[_0-9]*",),
                 "get_file_regex(context,'OUTCAR[_0-9]*','\s+NELECT\s*\=\s*(?P<value>%s)\s+(?P<unit>.*)$',False)" % number),
                 
                 ('ISIF',("OUTCAR[_0-9]*",),
                 "get_file_regex(context,'OUTCAR[_0-9]*','\s+ISIF\s+\=\s+(?P<value>%s)\s+(?P<unit>.*)$',False)" % number), 
                 
                 ('ISPIN',("OUTCAR[0-9]*",),
                 "get_file_regex(context,'OUTCAR[_0-9]*','\s+ISPIN\s+\=\s+(?P<value>%s)\s+(?P<unit>.*)$',False)" % number),
                 
                 ('Walltime',("^vasp.*[_0-9]*\.o(\d+)$",),
                 "get_file_regex(context,'^vasp.*[_0-9]*\.o(\d+)$','Elapsed time:\s+(?P<value>[\w:]+)(?P<unit>)',True)"),
                 
                 ('Number Of CPUs',("^vasp.*[_0-9]*\.o(\d+)$",),
                 "get_file_regex(context,'^vasp.*[_0-9]*\.o(\d+)$','Number of cpus:\s+(?P<value>.+)(?P<unit>)',True)"),
                 
                 ('Maximum virtual memory',("^vasp.*[_0-9]*\.o(\d+)$",),
                 "get_file_regex(context,'^vasp.*[_0-9]*\.o(\d+)$','Max virtual memory:\s+(?P<value>[0-9]+)(?P<unit>(M|G|K)B)',True)"),
                 
                 ('Max jobfs disk use',("^vasp.*[_0-9]*\.o(\d+)$",),
                 "get_file_regex(context,'^vasp.*[_0-9]*\.o(\d+)$','Max jobfs disk use:\s+(?P<value>.*)(?P<unit>(M|G|K)B)',True)"),
                 
                 
                 ('NSW',("OUTCAR[_0-9]*",),
                 "get_file_regex(context,'OUTCAR[_0-9]*','NSW\s*\=\s*(?P<value>%s)\s*(?P<unit>.*)$',False)" % number),
                
                 ('IBRION',("OUTCAR[_0-9]*",),
                 "get_file_regex(context,'OUTCAR[_0-9]*','IBRION\s*\=\s*(?P<value>%s)\s+(?P<unit>.*)$',False)" % number),
            
            
                 ('ISMEAR',("OUTCAR[_0-9]*",),
                 "get_file_regex(context,'OUTCAR[_0-9]*','ISMEAR\s*\=\s*(?P<value>%s)(?P<unit>)',False)" % number),
            
            
                 ('POTIM',("OUTCAR[_0-9]*",),
                 "get_file_regex(context,'OUTCAR[_0-9]*','POTIM\s*\=\s*(?P<value>%s)(?P<unit>)',False)" % number),
                 
                 ('MAGMOM',("POSCAR[_0-9]*",),
                 "get_file_lines(context,'POSCAR[_0-9]*',1,4)"), 
                 
                 ('Descriptor Line',("INCAR[_0-9]*",),
                 "get_file_regex(context,'INCAR[_0-9]*','System = (?P<value>.*)(?P<unit>)',False)"), 
       
                 ('EDIFF',("OUTCAR[_0-9]*",),
                 "get_file_regex(context,'OUTCAR[_0-9]*','EDIFF\s*\=\s*(?P<value>[^\s]+)(?P<unit>)',False)"), 
                 
                 ('EDIFFG',("OUTCAR[_0-9]*",),
                 "get_file_regex(context,'OUTCAR[_0-9]*','EDIFFG\s*\=\s*(?P<value>[^\s]+)(?P<unit>)',False)"), 
                 
                 
                 ('NELM',("OUTCAR[_0-9]*",),
                 "get_file_regex(context,'OUTCAR[_0-9]*','NELM\s*\=\s*(?P<value>[^;\s]+)(?P<unit>)',False)"), 
                 
                 ('ISTART',("INCAR[_0-9]*",),
                 "get_file_regex(context,'INCAR[_0-9]*','ISTART\s*\=\s*(?P<value>[^;\s]+)(?P<unit>)',False)"), 
                 
                 
                 ('TEBEG',("OUTCAR[_0-9]*",),
                 "get_file_regex(context,'OUTCAR[_0-9]*','TEBEG\s*\=\s*(?P<value>[^;\s]+)(?P<unit>)',False)"), 
                 
                  ('TEEND',("OUTCAR[_0-9]*",),
                 "get_file_regex(context,'OUTCAR[_0-9]*','TEEND\s*\=\s*(?P<value>[^;\s]+)(?P<unit>.*)',False)"), 
              
              
                 ('SMASS',("OUTCAR[_0-9]*",),
                 "get_file_regex(context,'OUTCAR[_0-9]*','SMASS\s*\=\s*(?P<value>[^\s]+)(?P<unit>.*)',False)"), 
                 
                 ('Final Iteration',("OSZICAR[_0-9]*",),
                 "get_final_iteration(context,'OSZICAR[_0-9]*')"), 
                 
                 
                
                 ('Cell Parameters',("POSCAR[_0-9]*",),
                  "get_file_lines(context,'POSCAR[_0-9]*',1,5)")),
                 
                 
                 ('http://tardis.edu.au/schemas/siesta/1','siesta 1.0'):
                 [],
                 ('http://tardis.edu.au/schemas/test/1',''):(('Test',("R-2-2.tif",),
                  "get_constant(context,'99','foobars')"),
                 ('Test2',("R-2-2.tif","R-2-5.tif"),"get_constant(context,'hello','')"))
                 }
                      


def get_final_iteration(context,fileregex):
    """ Return the final iteration number from a VASP run 
    """
    filename = _get_file_from_regex(fileregex,context['ready'],False)
    logger.debug("filename=%s" % filename)
    if not filename or filename not in context['ready']:
        logger.debug("found None")
        return ("","")
    else:
        logger.debug("found ready %s" % filename)
        datafile = context['ready'][filename]
        url = datafile.get_download_url()
        
        if datafile.protocol == 'tardis' or datafile.url.startswith('tardis'):
            raw_path = url.partition('//')[2]
            file_path = path.join(settings.FILE_STORE_PATH,
                                  str(context['expid']),
                                  str(datafile.dataset.id),
                                  raw_path,datafile.url.partition('//')[2])
        
            logger.debug("file_path=%s" % file_path)
        
            file_handle = open(file_path,"r")
            regex = "RMM\:\s*(?P<value>\d+)\s*"
            regx = re.compile(regex)
            max_value = 0
            for line in file_handle:
                logger.debug("line=%s" % line)
                match = regx.search(line)
                
                if match:
                    val = match.group('value') 
                    try:
                        value = int(val)
                    except ValueError:
                        value = 0
                    logger.debug("value=%s" % value)
                    if value > max_value:
                        max_value = value            
            file_handle.close()
            logger.debug("max_value = %s" % max_value)
            return (max_value,"") 
        return ("","")   
    

def _get_file_from_regex(regex,context, return_max):
    """Returns the single key from ready dict which matches the regex.
    If return_max, then only use file which the largest group match in regex
    """
    regx = re.compile(regex)
    logger.debug("return_max=%s" % return_max)
    key = None
    max_match = ""
    max_value = 0
    logger.debug("regex=%s" % regex)
    for key in dict(context):
        logger.debug("key=%s" % key)
        match = regx.match(key)
        logger.debug("match=%s" % match)
        if return_max:
            logger.debug("return_max")
            if match:
                logger.debug("match=%s" % match)
                matched_groups = match.groups()
                if matched_groups:
                    if len(matched_groups) == 1:
                        if matched_groups[0] > max_value:
                            max_match = key
                            max_value=matched_groups[0]
        else:
            if match:
                logger.debug("matched to %s" % str(match.group(0)))
                return match.group(0) 
            
    logger.debug("max_match=%s" % max_match)
    return max_match

def get_file_lines(context,fileregex, linestart,lineend):
    """ Returns value and units from the filenameregex where value is 
    newline joined lines from linestart to lineend.  Only works for local files""" 
    # match fileregex to available files
    #regx = re.compile(fileregex)
    #filename = None
    #for key in context['ready']:
    #    match = regx.match(key)
    #    if match:
    #        filename = key
    #        break
    filename = _get_file_from_regex(fileregex,context['ready'],False)
    if filename not in context['ready']:
        return (None,'')
    else:
        datafile = context['ready'][filename]
        url = datafile.get_download_url()
        # FIXME: add other protocols
        if datafile.protocol == 'tardis' or datafile.url.startswith('tardis'):
            raw_path = url.partition('//')[2]
            file_path = path.join(settings.FILE_STORE_PATH,
                                  str(context['expid']),
                                  str(datafile.dataset.id),
                                  raw_path,datafile.url.partition('//')[2])
            file_handle = open(file_path,"r")
            res = []
            for i,line in enumerate(file_handle):
                if i in range(linestart,lineend):
                    res.append(line)
             
            return ("\n".join(res),'')
    return ('','')
    
    
def get_file_line(context,fileregex,lineno):
    """Returns the context of relative linenumber
    Assumes no units value and only works for smallish file"""
    # match fileregex to available files
    #regx = re.compile(fileregex)
    #filename = None
    #for key in context['ready']:
        #match = regx.match(key)
        #if match:
            #filename = key
            #break
    filename = _get_file_from_regex(fileregex,context['ready'],False)
    if filename not in context['ready']:
        return (None,'')
    else:
        datafile = context['ready'][filename]
        url = datafile.get_download_url()
        
        if datafile.protocol == 'tardis' or datafile.url.startswith('tardis'):
            raw_path = url.partition('//')[2]
            file_path = path.join(settings.FILE_STORE_PATH,
                                  str(context['expid']),
                                  str(datafile.dataset.id),
                                  raw_path,datafile.url.partition('//')[2])
        
            print "file_path=%s" % file_path
        
            #FIXME: does not work for large files
        
            file_handle = open(file_path,"r")
            line_list = file_handle.readlines()
        
            file_handle.close()
            print line_list 
            return (str(line_list[lineno]),'')
    return (None,'')  
    
        
def get_file_regex(context,fileregex,regex,return_max):
    """ Searches all files that match file regex and searches for regex in contents.
        Returns the contents of groups 'name' and 'unit' as a tuple
    """

    # match fileregex to available files
    #regx = re.compile(fileregex)
    #filename = None
    #for key in context['ready']:
    #    match = regx.match(key)
    #    if match:
    #        filename = key
    #        break
    
    filename = _get_file_from_regex(fileregex,context['ready'],return_max)
    
    if not filename or filename not in context['ready']:
        print "found None"
        return ('','')
    else:
        print "found ready %s" % filename
        datafile = context['ready'][filename]
        url = datafile.get_download_url()
        
        if datafile.protocol == 'tardis' or datafile.url.startswith('tardis'):
            raw_path = url.partition('//')[2]
            file_path = path.join(settings.FILE_STORE_PATH,
                                  str(context['expid']),
                                  str(datafile.dataset.id),
                                  raw_path,datafile.url.partition('//')[2])
        
            print "file_path=%s" % file_path
        
            file_handle = open(file_path,"r")
          
            regx = re.compile(regex)
            for line in file_handle:
                match = regx.search(line)
                
                if match:
                    value = match.group('value')
                    unit = str(match.group('unit'))
                    if not unit:
                        unit = ''
                    print "value=%s unit=%s" % (value,unit)
                    file_handle.close()
                    res = (value,unit)
                    for g in res:
                        print "final matched %s" % g
                    return res
            file_handle.close() 
        return ('','')     
    
def get_constant(context,val,unit):
    return (val,unit)

    
    
            
def get_metadata(ruleset):
    from collections import defaultdict
    
    # TODO: handle files that have not arrived yet
    expectedmd5 = None
                  
    #TODO: missing values default to STRING, but later could be numeric when have value
    metadatas = {}
    for exp in Experiment.objects.all():
        logger.debug("exp=%s\n" % exp)
        for dataset in Dataset.objects.filter(experiment=exp):
            meta = {}
            logger.debug("\tdataset=%s\n" % dataset)
            ready = defaultdict()
            for datafile in Dataset_File.objects.filter(dataset=dataset):
                logger.debug("\t\tdatafile=%s\n" % str(datafile))
                ready[datafile.filename] = datafile
                if datafile not in ready:
                    logger.debug(datafile.md5sum + "\n")
                    try:
                        datafile._set_md5sum() 
                    except IOError:
                        pass
                    except OSError:
                        pass
                    logger.debug("hello from %s\n" % datafile)
                    #if (datafile.md5sum == datafile.expectedmd5):
                    #    ready[datafile] = True
                    
            logger.debug("ready=%s\n" % ready)
            for tagname,file_patterns,code in ruleset:
                logger.debug("file_patterns=%s,code=%s\n" % (file_patterns,code))
            
                # check whether we have all files available.
                # f could have _number regex
                count = 0
                for file_pattern in file_patterns:
                    import re
                    rule_file_regx = re.compile(file_pattern)
                    filename = None
                    # ready files could have _number prefix
                    for datafilename in ready:
                        match = rule_file_regx.match(datafilename)
                        if match:
                            logger.debug("matched % s" % datafilename)
                            filename = datafilename
                            break
                    logger.debug("filename=%s\n" % filename)
                    if filename in ready:
                        count += 1
                logger.debug("count=%d" % count)
                if count == len(file_patterns):
                    logger.debug("ready to start extracting on %s files\n" % count)
                    data_context = {'expid':exp.id,
                               'ready':ready}
                    logger.debug("data_context=%s" % data_context)
                    try:
                        (value,unit) = eval(code,{},
                                         {"get_file_line":get_file_line,
                                          "get_file_lines":get_file_lines,
                                          "get_file_regex":get_file_regex,
                                          "get_final_iteration":get_final_iteration,
                                          "get_constant":get_constant,
                                          'context':data_context})
                    except Exception,e:
                        logger.error("Exception %s" % e)
                    logger.debug("value,unit=%s %s" % (value,unit))
                 
                    meta[tagname] = (value,unit)
                     
            logger.debug("meta=%s\n" % meta)
            metadatas[dataset] = meta
        
    return metadatas
            
def get_schema(schema,name):
    """Return the schema object that the paramaterset will use.
    """
    try:
        return Schema.objects.get(namespace__exact=schema)
    except Schema.DoesNotExist:
        schema = Schema(namespace=schema, name=name,
                        type=Schema.DATASET)
        schema.save()
        return schema          
            
def get_parameters(schema,metadata):
    
    param_objects = ParameterName.objects.filter(schema=schema)
    logger.debug("param_objects=%s\n" % param_objects)
    parameters = []
    
    for p in metadata.keys():
        logger.debug("pp=%s\n" % p)
        logger.debug("metadata[pp][0] = %s" % metadata[p][0])
        logger.debug("metadata[pp][1] = %s" % metadata[p][1])
        parameter = filter(lambda x: x.name == p,param_objects)
        logger.debug("pparameter=%s\n" % parameter)
        if parameter:
            parameters.append(parameter[0])
            continue
        
        datatype = ParameterName.STRING
        units = None
        
        try:
            int(metadata[p][0])
        except (ValueError,TypeError):
            pass
        else:
            datatype = ParameterName.NUMERIC
            units = str(metadata[p][1])
        
        try:
            float(metadata[p][0])
        except (ValueError,TypeError):
            pass
        else:
            datatype = ParameterName.NUMERIC
            units = str(metadata[p][1])
        
        logger.debug("units=%s" % str(metadata[p][1]))
        if units:
            new_param = ParameterName(schema=schema,
                                  name=p,
                                  full_name=p,
                                  data_type=datatype,
                                  units=units)
        else:
            new_param = ParameterName(schema=schema,
                                  name=p,
                                  full_name=p,
                                  data_type=datatype)
        
        new_param.save()
        logger.debug("new_param=%s" % new_param)
        logger.debug("datatype=%s" % datatype)
        parameters.append(new_param)
    return parameters

def save_metadata(instance,schema,metadata):
    parameters = get_parameters(schema, metadata)
    logger.debug("parameters=%s" % parameters)
    if not parameters:
        return None
      
    try:
        ps = DatasetParameterSet.objects.get(schema=schema,
                                                dataset=instance)
        #return ps
    except DatasetParameterSet.DoesNotExist:
        ps = DatasetParameterSet(schema=schema,dataset=instance)
        ps.save()
        
    logger.debug("ps=%s\n" % ps)
    logger.debug("metadata2=%s\n" % metadata)
        
    for p in parameters:
        logger.debug("p=%s\n" % p)
        if p.name in metadata:
            logger.debug("found p =%s %s\n" % (p.name,p.units))
            try:
                dfp = DatasetParameter.objects.get(parameterset=ps,name=p)
            except DatasetParameter.DoesNotExist:           
                dfp = DatasetParameter(parameterset=ps,
                                    name=p)
          
            # TODO: handle bad type 
            if p.isNumeric():
                dfp.numerical_value = metadata[p.name][0]
                logger.debug("numeric")
            else:
                dfp.string_value = metadata[p.name][0]
            logger.debug("dfp=%(dfp)s" % locals())
            dfp.save()
            
            
def go():
    
    for schemainfo in rulesets:
        metadatas = get_metadata(rulesets[schemainfo])
        logger.debug("metadatas=%s\n" % metadatas)
    
        schema = get_schema(schemainfo[0],schemainfo[1])
    
        for metadata in metadatas:
            save_metadata(metadata,schema,metadatas[metadata])

      
                   