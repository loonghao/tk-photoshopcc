# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class PhotoshopCCSceneCollector(HookBaseClass):
    """
    Collector that operates on the current photoshop document. Should inherit
    from the basic collector hook.
    """

    @property
    def settings(self):
        """
        Dictionary defining the settings that this collector expects to receive
        through the settings parameter in the process_current_session and
        process_file methods.

        A dictionary on the following form::

            {
                "Settings Name": {
                    "type": "settings_type",
                    "default": "default_value",
                    "description": "One line description of the setting"
            }

        The type string should be one of the data types that toolkit accepts as
        part of its environment configuration.
        """

        # grab any base class settings
        collector_settings = \
            super(PhotoshopCCSceneCollector, self).settings or {}

        # settings specific to this collector
        photoshop_session_settings = {
            "Work Template": {
                "type": "template",
                "default": None,
                "description": "Template path for artist work files. Should "
                               "correspond to a template defined in "
                               "templates.yml. If configured, is made available"
                               "to publish plugins via the collected item's "
                               "properties. ",
            },
        }

        # update the base settings with these settings
        collector_settings.update(photoshop_session_settings)

        return collector_settings

    def process_current_session(self, settings, parent_item):
        """
        Analyzes the open documents in Photoshop and creates publish items
        parented under the supplied item.

        :param dict settings: Configured settings for this collector
        :param parent_item: Root item instance
        """

        # go ahead and build the path to the icon for use by any documents
        icon_path = os.path.join(
            self.disk_location,
            os.pardir,
            "icons",
            "photoshop.png"
        )

        publisher = self.parent
        engine = publisher.engine

        # get the active document name
        try:
            active_doc_name = engine.adobe.app.activeDocument.name
        except RuntimeError:
            engine.logger.debug("No active document found.")
            active_doc_name = None

        # attempt to retrive a configured work template. we can attach
        # it to the collected project items
        work_template_setting = settings.get("Work Template")
        work_template = None
        if work_template_setting:
            work_template = publisher.engine.get_template_by_name(
                work_template_setting.value)

        # iterate over all open documents and add them as publish items
        for document in engine.adobe.app.documents:

            # create a publish item for the document
            document_item = parent_item.create_item(
                "photoshop.document",
                "Photoshop Image",
                document.name
            )

            document_item.set_icon_from_path(icon_path)

            # disable thumbnail creation for photoshop documents. for the
            # default workflow, the thumbnail will be auto-updated after the
            # version creation plugin runs
            document_item.thumbnail_enabled = False

            # add the document object to the properties so that the publish
            # plugins know which open document to associate with this item
            document_item.properties["document"] = document

            doc_name = document.name

            self.logger.info("Collected Photoshop document: %s" % (doc_name))

            # enable the active document and expand it. other documents are
            # collapsed and disabled.
            if active_doc_name and doc_name == active_doc_name:
                document_item.expanded = True
                document_item.checked = True
            elif active_doc_name:
                # there is an active document, but this isn't it. collapse and
                # disable this item
                document_item.expanded = False
                document_item.checked = False

            path = _document_path(document)

            if path:
                # try to set the thumbnail for display. won't display anything
                # for psd/psb, but others should work.
                document_item.set_thumbnail_from_path(path)

            # store the template on the item for use by publish plugins. we
            # can't evaluate the fields here because there's no guarantee the
            # current session path won't change once the item has been created.
            # the attached publish plugins will need to resolve the fields at
            # execution time.
            if work_template:
                document_item.properties["work_template"] = work_template
                self.logger.debug(
                    "Work template defined for Photoshop collection.")


def _document_path(document):
    """
    Returns the path on disk to the supplied document. May be ``None`` if the
    document has not been saved.
    """

    try:
        path = document.fullName.fsName
    except RuntimeError:
        path = None

    return path