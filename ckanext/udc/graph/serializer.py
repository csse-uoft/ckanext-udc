import rdflib
from rdflib.plugins.serializers.turtle import TurtleSerializer
from rdflib.serializer import Serializer

class SPARQLInsertSerializer(TurtleSerializer):
    def startDocument(self):
        self._started = True
        ns_list = sorted(self.namespaces.items())

        # Override prefix formats
        if self.base:
            self.write(self.indent() + "PREFIX : <%s> \n" % self.base)
        for prefix, uri in ns_list:
            self.write(self.indent() + "PREFIX %s: <%s> \n" % (prefix, uri))
        if ns_list and self._spacious:
            self.write("\n")
        self.write("INSERT DATA {\n")

    def endDocument(self):
        if self._spacious:
            self.write("\n")
        self.write("}")
    
    # def s_default(self, subject):
    #     properties = self.buildPredicateHash(subject)
    #     # SKip empty instances
    #     if len(properties) == 1 and [*properties.keys()][0] == rdflib.RDF.type:
    #         return False
    #     return super().s_default(subject)



rdflib.plugin.register('sparql-insert', Serializer, 'ckanext.udc.graph.serializer', 'SPARQLInsertSerializer')
