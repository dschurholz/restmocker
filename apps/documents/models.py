# -*- coding: utf-8 -*-

import re
import time
import hashlib

from datetime import date
from os.path import basename

from django.db import models 
from django.template import Context
from django.template import Template
from django.contrib.sites.models import Site

from django_extensions.db.fields import CreationDateTimeField
from django_extensions.db.fields import ModificationDateTimeField

from documents import constants, strings

class Realm(models.Model):
    name = models.CharField(strings.NAME, max_length=128, unique=True)
    prefix = models.SlugField(strings.PREFIX)
    description = models.TextField(strings.DESCRIPTION)
    created_at = CreationDateTimeField(strings.CREATED_AT)
    updated_at = ModificationDateTimeField(strings.UPDATED_AT)

    class Meta:
        ordering = ('name','created_at', )
        verbose_name = strings.REALM
        verbose_name_plural = strings.REALM_PLURAL

    def __unicode__(self):
        return self.name

    def apply_text_substitutions(self, text):
        substitutions = self.textsubstitution_set.all()
        for s in substitutions:
            regexp = re.compile(s.regexp)
            result = regexp.subn(s.sub, text)
            text = result[0]
        return text
    
class Document(models.Model):
    """
    Represents a response returned by the web service.
    """
    realm = models.ForeignKey(Realm, verbose_name=strings.REALM)
    title = models.CharField(strings.TITLE, max_length=128)
    regexp = models.CharField(strings.REGEXP, max_length=255)
    template = models.TextField(strings.TEMPLATE)
    description = models.TextField(strings.DESCRIPTION, null=True, blank=True)
    mime_type = models.CharField(strings.MIME_TYPE, max_length=128, 
        default='application/json')
    sample_uri = models.CharField(strings.SAMPLE_URI, max_length=255, null=True, blank=True)
    created_at = CreationDateTimeField(strings.CREATED_AT)
    updated_at = ModificationDateTimeField(strings.UPDATED_AT)

    class Meta:
        ordering = ('title','created_at', )
        verbose_name = strings.DOCUMENT
        verbose_name_plural = strings.DOCUMENT_PLURAL

    def __unicode__(self):
        return self.title

    def get_regexp(self):
        return re.compile(self.regexp)

    def match(self, uri_fragment):
        regexp = self.get_regexp()
        return bool(regexp.match(uri_fragment))

    def get_context_dict(self, uri_fragment):
        result = {}
        regexp = self.get_regexp()
        m = regexp.match(uri_fragment)
        if m is not None:
            result = m.groupdict()
        return result

    def render_template(self, uri_fragment):
        t = Template(self.template)
        c = Context(self.get_context_dict(uri_fragment))
        result = t.render(c)
        result = self.realm.apply_text_substitutions(result)
        return result

    def get_last_modified(self):
        return self.updated_at if self.updated_at else self.created_at

    def get_etag(self):
        ts = self.get_last_modified()
        return hashlib.sha1(str(ts)).hexdigest()

    def get_sample_uri(self):
        site = Site.objects.get_current()
        parts = []
        parts.append('http://')
        parts.append(site.domain)
        parts.append('/api/')
        parts.append(self.realm.prefix)
        parts.append(self.sample_uri)
        return ''.join(parts)

class TextSubstitution(models.Model):
    """
    Represents some text to be replaced in the documents of a realm.
    """
    realm = models.ForeignKey(Realm, verbose_name=strings.REALM)
    regexp = models.CharField(strings.REGEXP, max_length=255)
    sub = models.CharField(strings.TEXT_SUBSTITUTION, max_length=255)
    created_at = CreationDateTimeField(strings.CREATED_AT)
    updated_at = ModificationDateTimeField(strings.UPDATED_AT)

    class Meta:
        ordering = ('realm', 'created_at', )
        verbose_name = strings.TEXT_SUBSTITUTION
        verbose_name_plural = strings.TEXT_SUBSTITUTION_PLURAL

    def __unicode__(self):
        return self.regexp