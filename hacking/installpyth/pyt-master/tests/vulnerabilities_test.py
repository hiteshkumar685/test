import os

from .base_test_case import BaseTestCase
from pyt import trigger_definitions_parser, vulnerabilities
from pyt.base_cfg import Node
from pyt.constraint_table import constraint_table, initialize_constraint_table
from pyt.fixed_point import analyse
from pyt.framework_adaptor import FrameworkAdaptor
from pyt.framework_helper import is_flask_route_function
from pyt.lattice import Lattice
from pyt.reaching_definitions_taint import ReachingDefinitionsTaintAnalysis


class EngineTest(BaseTestCase):
    def run_empty(self):
        return

    def get_lattice_elements(self, cfg_nodes):
        """Dummy analysis method"""
        return cfg_nodes

    def test_parse(self):
        definitions = vulnerabilities.parse(trigger_word_file=os.path.join(os.getcwd(), 'pyt', 'trigger_definitions', 'test_triggers.pyt'))

        self.assert_length(definitions.sources, expected_length=1)
        self.assert_length(definitions.sinks, expected_length=3)
        self.assert_length(definitions.sinks[0][1], expected_length=1)
        self.assert_length(definitions.sinks[1][1], expected_length=3)

    def test_parse_section(self):
        l = list(trigger_definitions_parser.parse_section(iter(['get'])))
        self.assert_length(l, expected_length=1)
        self.assertEqual(l[0][0], 'get')
        self.assertEqual(l[0][1], list())

        l = list(trigger_definitions_parser.parse_section(iter(['get', 'get -> a, b, c d s aq     a'])))
        self.assert_length(l, expected_length=2)
        self.assertEqual(l[0][0], 'get')
        self.assertEqual(l[1][0], 'get')
        self.assertEqual(l[1][1], ['a', 'b', 'c d s aq     a'])
        self.assert_length(l[1][1], expected_length=3)

    def test_label_contains(self):
        cfg_node = Node('label', None, line_number=None, path=None)
        trigger_words = [('get', [])]
        l = list(vulnerabilities.label_contains(cfg_node, trigger_words))
        self.assert_length(l, expected_length=0)

        cfg_node = Node('request.get("stefan")', None, line_number=None, path=None)
        trigger_words = [('get', []), ('request', [])]
        l = list(vulnerabilities.label_contains(cfg_node, trigger_words))
        self.assert_length(l, expected_length=2)

        trigger_node_1 = l[0]
        trigger_node_2 = l[1]
        self.assertEqual(trigger_node_1.trigger_word, 'get')
        self.assertEqual(trigger_node_1.cfg_node, cfg_node)
        self.assertEqual(trigger_node_2.trigger_word, 'request')
        self.assertEqual(trigger_node_2.cfg_node, cfg_node)

        cfg_node = Node('request.get("stefan")', None, line_number=None, path=None)
        trigger_words = [('get', []), ('get', [])]
        l = list(vulnerabilities.label_contains(cfg_node, trigger_words))
        self.assert_length(l, expected_length=2)

    def test_find_triggers(self):
        self.cfg_create_from_file('example/vulnerable_code/XSS.py')

        cfg_list = [self.cfg]

        FrameworkAdaptor(cfg_list, [], [], is_flask_route_function)

        XSS1 = cfg_list[1]
        trigger_words = [('get', [])]

        l = vulnerabilities.find_triggers(XSS1.nodes, trigger_words)
        self.assert_length(l, expected_length=1)


    def test_find_sanitiser_nodes(self):
        cfg_node = Node(None, None, line_number=None, path=None)
        sanitiser_tuple  = vulnerabilities.Sanitiser('escape', cfg_node)
        sanitiser = 'escape'

        result = list(vulnerabilities.find_sanitiser_nodes(sanitiser, [sanitiser_tuple]))
        self.assert_length(result, expected_length=1)
        self.assertEqual(result[0], cfg_node)


    def test_build_sanitiser_node_dict(self):
        self.cfg_create_from_file('example/vulnerable_code/XSS_sanitised.py')
        cfg_list = [self.cfg]

        FrameworkAdaptor(cfg_list, [], [], is_flask_route_function)

        cfg = cfg_list[1]

        cfg_node = Node(None, None,  line_number=None, path=None)
        sinks_in_file = [vulnerabilities.TriggerNode('replace', ['escape'], cfg_node)]

        sanitiser_dict = vulnerabilities.build_sanitiser_node_dict(cfg, sinks_in_file)
        self.assert_length(sanitiser_dict, expected_length=1)
        self.assertIn('escape', sanitiser_dict.keys())

        self.assertEqual(sanitiser_dict['escape'][0], cfg.nodes[3])

    def test_is_sanitised_false(self):
        cfg_node_1 = Node('Not sanitising at all', None, line_number=None, path=None)
        cfg_node_2 = Node('something.replace("this", "with this")', None, line_number=None, path=None)
        sinks_in_file = [vulnerabilities.TriggerNode('replace', ['escape'], cfg_node_2)]
        sanitiser_dict = {'escape': [cfg_node_1]}

        # We should use mock instead
        orginal_get_lattice_elements = ReachingDefinitionsTaintAnalysis.get_lattice_elements
        ReachingDefinitionsTaintAnalysis.get_lattice_elements = self.get_lattice_elements
        lattice = Lattice([cfg_node_1, cfg_node_2], analysis_type=ReachingDefinitionsTaintAnalysis)

        constraint_table[cfg_node_1] = 0b0
        constraint_table[cfg_node_2] = 0b0

        result = vulnerabilities.is_sanitised(sinks_in_file[0], sanitiser_dict, lattice)
        self.assertEqual(result, False)
        # Clean up
        ReachingDefinitionsTaintAnalysis.get_lattice_elements = orginal_get_lattice_elements


    def test_is_sanitised_true(self):
        cfg_node_1 = Node('Awesome sanitiser', None,  line_number=None, path=None)
        cfg_node_2 = Node('something.replace("this", "with this")', None, line_number=None, path=None)
        sinks_in_file = [vulnerabilities.TriggerNode('replace', ['escape'], cfg_node_2)]
        sanitiser_dict = {'escape': [cfg_node_1]}

        # We should use mock instead
        orginal_get_lattice_elements = ReachingDefinitionsTaintAnalysis.get_lattice_elements
        ReachingDefinitionsTaintAnalysis.get_lattice_elements = self.get_lattice_elements

        lattice = Lattice([cfg_node_1, cfg_node_2], analysis_type=ReachingDefinitionsTaintAnalysis)
        constraint_table[cfg_node_2] = 0b1

        result = vulnerabilities.is_sanitised(sinks_in_file[0], sanitiser_dict, lattice)
        self.assertEqual(result, True)
        # Clean up
        ReachingDefinitionsTaintAnalysis.get_lattice_elements = orginal_get_lattice_elements

    def run_analysis(self, path):
        self.cfg_create_from_file(path)
        cfg_list = [self.cfg]

        FrameworkAdaptor(cfg_list, [], [], is_flask_route_function)
        initialize_constraint_table(cfg_list)

        analyse(cfg_list, analysis_type=ReachingDefinitionsTaintAnalysis)

        return vulnerabilities.find_vulnerabilities(cfg_list, ReachingDefinitionsTaintAnalysis)

    def test_find_vulnerabilities_assign_other_var(self):
        vulnerability_log = self.run_analysis('example/vulnerable_code/XSS_assign_to_other_var.py')
        self.assert_length(vulnerability_log.vulnerabilities, expected_length=1)

    def test_find_vulnerabilities_inter_command_injection(self):
        vulnerability_log = self.run_analysis('example/vulnerable_code/inter_command_injection.py')
        self.assert_length(vulnerability_log.vulnerabilities, expected_length=1)

    def test_find_vulnerabilities_inter_command_injection_2(self):
        vulnerability_log = self.run_analysis('example/vulnerable_code/inter_command_injection_2.py')
        self.assert_length(vulnerability_log.vulnerabilities, expected_length=1)

    def test_XSS_result(self):
        vulnerability_log = self.run_analysis('example/vulnerable_code/XSS.py')
        self.assert_length(vulnerability_log.vulnerabilities, expected_length=1)
        vulnerability_description = str(vulnerability_log.vulnerabilities[0])
        EXPECTED_VULNERABILITY_DESCRIPTION = """
            File: example/vulnerable_code/XSS.py
             > User input at line 6, trigger word "get(":
                ¤call_1 = ret_request.args.get('param', 'not set')
            Reassigned in: 
                File: example/vulnerable_code/XSS.py
                 > Line 6: param = ¤call_1
                File: example/vulnerable_code/XSS.py
                 > Line 9: ¤call_3 = ret_make_response(¤call_4)
                File: example/vulnerable_code/XSS.py
                 > Line 9: resp = ¤call_3
                File: example/vulnerable_code/XSS.py
                 > Line 10: ret_XSS1 = resp
            File: example/vulnerable_code/XSS.py
             > reaches line 9, trigger word "replace(": 
                ¤call_4 = ret_html.replace('{{ param }}', param)
        """

        self.assertTrue(self.string_compare_alpha(vulnerability_description, EXPECTED_VULNERABILITY_DESCRIPTION))

    def test_command_injection_result(self):
        vulnerability_log = self.run_analysis('example/vulnerable_code/command_injection.py')
        self.assert_length(vulnerability_log.vulnerabilities, expected_length=1)
        vulnerability_description = str(vulnerability_log.vulnerabilities[0])
        EXPECTED_VULNERABILITY_DESCRIPTION = """
            File: example/vulnerable_code/command_injection.py
             > User input at line 15, trigger word "form[": 
                param = request.form['suggestion']
            Reassigned in: 
                File: example/vulnerable_code/command_injection.py
                 > Line 16: command = 'echo ' + param + ' >> ' + 'menu.txt'
            File: example/vulnerable_code/command_injection.py
             > reaches line 18, trigger word "subprocess.call(": 
                ¤call_1 = ret_subprocess.call(command, shell=True)
        """

        self.assertTrue(self.string_compare_alpha(vulnerability_description, EXPECTED_VULNERABILITY_DESCRIPTION))

    def test_path_traversal_result(self):
        vulnerability_log = self.run_analysis('example/vulnerable_code/path_traversal.py')
        self.assert_length(vulnerability_log.vulnerabilities, expected_length=1)
        vulnerability_description = str(vulnerability_log.vulnerabilities[0])
        EXPECTED_VULNERABILITY_DESCRIPTION = """
            File: example/vulnerable_code/path_traversal.py
             > User input at line 15, trigger word "get(":
                ¤call_1 = ret_request.args.get('image_name')
            Reassigned in: 
                File: example/vulnerable_code/path_traversal.py
                 > Line 15: image_name = ¤call_1
                File: example/vulnerable_code/path_traversal.py
                 > Line 10: save_3_image_name = image_name
                File: example/vulnerable_code/path_traversal.py
                 > Line 10: image_name = save_3_image_name
                File: example/vulnerable_code/path_traversal.py
                 > Line 19: temp_2_other_arg = image_name
                File: example/vulnerable_code/path_traversal.py
                 > Line 6: other_arg = temp_2_other_arg
                File: example/vulnerable_code/path_traversal.py
                 > Line 7: outer_ret_val = outer_arg + 'hey' + other_arg
                File: example/vulnerable_code/path_traversal.py
                 > Line 8: ret_outer = outer_ret_val
                File: example/vulnerable_code/path_traversal.py
                 > Line 19: ¤call_2 = ret_outer
                File: example/vulnerable_code/path_traversal.py
                 > Line 19: foo = ¤call_2
                File: example/vulnerable_code/path_traversal.py
                 > Line 6: save_2_image_name = image_name
                File: example/vulnerable_code/path_traversal.py
                 > Line 6: image_name = save_2_image_name
            File: example/vulnerable_code/path_traversal.py
             > reaches line 20, trigger word "send_file(":
                ¤call_4 = ret_send_file(foo)
        """

        self.assertTrue(self.string_compare_alpha(vulnerability_description, EXPECTED_VULNERABILITY_DESCRIPTION))

    def test_path_traversal_sanitised_result(self):
        vulnerability_log = self.run_analysis('example/vulnerable_code/path_traversal_sanitised.py')
        self.assert_length(vulnerability_log.vulnerabilities, expected_length=1)
        vulnerability_description = str(vulnerability_log.vulnerabilities[0])
        EXPECTED_VULNERABILITY_DESCRIPTION = """
            File: example/vulnerable_code/path_traversal_sanitised.py
             > User input at line 8, trigger word "get(":
                ¤call_1 = ret_request.args.get('image_name')
            Reassigned in: 
                File: example/vulnerable_code/path_traversal_sanitised.py
                 > Line 8: image_name = ¤call_1
                File: example/vulnerable_code/path_traversal_sanitised.py
                 > Line 10: image_name = ¤call_2
                File: example/vulnerable_code/path_traversal_sanitised.py
                 > Line 12: ¤call_4 = ret_os.path.join(¤call_5, image_name)
                File: example/vulnerable_code/path_traversal_sanitised.py
                 > Line 12: ret_cat_picture = ¤call_3
            File: example/vulnerable_code/path_traversal_sanitised.py
             > reaches line 12, trigger word "send_file(":
                ¤call_3 = ret_send_file(¤call_4)
            This vulnerability is potentially sanitised by: ["'..'", "'..' in"]
        """

        self.assertTrue(self.string_compare_alpha(vulnerability_description, EXPECTED_VULNERABILITY_DESCRIPTION))

    def test_sql_result(self):
        vulnerability_log = self.run_analysis('example/vulnerable_code/sql/sqli.py')
        self.assert_length(vulnerability_log.vulnerabilities, expected_length=1)
        vulnerability_description = str(vulnerability_log.vulnerabilities[0])
        EXPECTED_VULNERABILITY_DESCRIPTION = """
            File: example/vulnerable_code/sql/sqli.py
             > User input at line 26, trigger word "get(":
                ¤call_1 = ret_request.args.get('param', 'not set')
            Reassigned in: 
                File: example/vulnerable_code/sql/sqli.py
                 > Line 26: param = ¤call_1
                File: example/vulnerable_code/sql/sqli.py
                 > Line 27: result = ¤call_2
            File: example/vulnerable_code/sql/sqli.py
             > reaches line 27, trigger word "execute(": 
                ¤call_2 = ret_db.engine.execute(param)
        """

        self.assertTrue(self.string_compare_alpha(vulnerability_description, EXPECTED_VULNERABILITY_DESCRIPTION))

    def test_XSS_form_result(self):
        vulnerability_log = self.run_analysis('example/vulnerable_code/XSS_form.py')
        self.assert_length(vulnerability_log.vulnerabilities, expected_length=1)
        vulnerability_description = str(vulnerability_log.vulnerabilities[0])
        EXPECTED_VULNERABILITY_DESCRIPTION = """
            File: example/vulnerable_code/XSS_form.py
             > User input at line 14, trigger word "form[": 
                data = request.form['my_text']
            Reassigned in: 
                File: example/vulnerable_code/XSS_form.py
                 > Line 15: ¤call_1 = ret_make_response(¤call_2)
                File: example/vulnerable_code/XSS_form.py
                 > Line 15: resp = ¤call_1
                File: example/vulnerable_code/XSS_form.py
                 > Line 17: ret_example2_action = resp
            File: example/vulnerable_code/XSS_form.py
             > reaches line 15, trigger word "replace(": 
                ¤call_2 = ret_html1.replace('{{ data }}', data)
        """

        self.assertTrue(self.string_compare_alpha(vulnerability_description, EXPECTED_VULNERABILITY_DESCRIPTION))

    def test_XSS_url_result(self):
        vulnerability_log = self.run_analysis('example/vulnerable_code/XSS_url.py')
        self.assert_length(vulnerability_log.vulnerabilities, expected_length=1)
        vulnerability_description = str(vulnerability_log.vulnerabilities[0])
        EXPECTED_VULNERABILITY_DESCRIPTION = """
            File: example/vulnerable_code/XSS_url.py
             > User input at line 4, trigger word "Flask function URL parameter": 
                url
            Reassigned in: 
                File: example/vulnerable_code/XSS_url.py
                 > Line 6: param = url
                File: example/vulnerable_code/XSS_url.py
                 > Line 9: ¤call_2 = ret_make_response(¤call_3)
                File: example/vulnerable_code/XSS_url.py
                 > Line 9: resp = ¤call_2
                File: example/vulnerable_code/XSS_url.py
                 > Line 10: ret_XSS1 = resp
            File: example/vulnerable_code/XSS_url.py
             > reaches line 9, trigger word "replace(": 
                ¤call_3 = ret_html.replace('{{ param }}', param)
        """

        self.assertTrue(self.string_compare_alpha(vulnerability_description, EXPECTED_VULNERABILITY_DESCRIPTION))

    def test_XSS_no_vuln_result(self):
        vulnerability_log = self.run_analysis('example/vulnerable_code/XSS_no_vuln.py')
        self.assert_length(vulnerability_log.vulnerabilities, expected_length=0)

    def test_XSS_reassign_result(self):
        vulnerability_log = self.run_analysis('example/vulnerable_code/XSS_reassign.py')
        self.assert_length(vulnerability_log.vulnerabilities, expected_length=1)
        vulnerability_description = str(vulnerability_log.vulnerabilities[0])
        EXPECTED_VULNERABILITY_DESCRIPTION = """
            File: example/vulnerable_code/XSS_reassign.py
             > User input at line 6, trigger word "get(":
                ¤call_1 = ret_request.args.get('param', 'not set')
            Reassigned in: 
                File: example/vulnerable_code/XSS_reassign.py
                 > Line 6: param = ¤call_1
                File: example/vulnerable_code/XSS_reassign.py
                 > Line 8: param = param + ''
                File: example/vulnerable_code/XSS_reassign.py
                 > Line 11: ¤call_3 = ret_make_response(¤call_4)
                File: example/vulnerable_code/XSS_reassign.py
                 > Line 11: resp = ¤call_3
                File: example/vulnerable_code/XSS_reassign.py
                 > Line 12: ret_XSS1 = resp
            File: example/vulnerable_code/XSS_reassign.py
             > reaches line 11, trigger word "replace(": 
                ¤call_4 = ret_html.replace('{{ param }}', param)
        """

        self.assertTrue(self.string_compare_alpha(vulnerability_description, EXPECTED_VULNERABILITY_DESCRIPTION))

    def test_XSS_sanitised_result(self):
        vulnerability_log = self.run_analysis('example/vulnerable_code/XSS_sanitised.py')
        self.assert_length(vulnerability_log.vulnerabilities, expected_length=1)
        vulnerability_description = str(vulnerability_log.vulnerabilities[0])
        EXPECTED_VULNERABILITY_DESCRIPTION = """
            File: example/vulnerable_code/XSS_sanitised.py
             > User input at line 7, trigger word "get(":
                ¤call_1 = ret_request.args.get('param', 'not set')
            Reassigned in: 
                File: example/vulnerable_code/XSS_sanitised.py
                 > Line 7: param = ¤call_1
                File: example/vulnerable_code/XSS_sanitised.py
                 > Line 9: ¤call_2 = ret_Markup.escape(param)
                File: example/vulnerable_code/XSS_sanitised.py
                 > Line 9: param = ¤call_2
                File: example/vulnerable_code/XSS_sanitised.py
                 > Line 12: ¤call_4 = ret_make_response(¤call_5)
                File: example/vulnerable_code/XSS_sanitised.py
                 > Line 12: resp = ¤call_4
                File: example/vulnerable_code/XSS_sanitised.py
                 > Line 13: ret_XSS1 = resp
            File: example/vulnerable_code/XSS_sanitised.py
             > reaches line 12, trigger word "replace(": 
                ¤call_5 = ret_html.replace('{{ param }}', param)
            This vulnerability is potentially sanitised by: ['escape']
        """

        self.assertTrue(self.string_compare_alpha(vulnerability_description, EXPECTED_VULNERABILITY_DESCRIPTION))

    def test_XSS_variable_assign_no_vuln_result(self):
        vulnerability_log = self.run_analysis('example/vulnerable_code/XSS_variable_assign_no_vuln.py')
        self.assert_length(vulnerability_log.vulnerabilities, expected_length=0)

    def test_XSS_variable_assign_result(self):
        vulnerability_log = self.run_analysis('example/vulnerable_code/XSS_variable_assign.py')
        self.assert_length(vulnerability_log.vulnerabilities, expected_length=1)
        vulnerability_description = str(vulnerability_log.vulnerabilities[0])
        EXPECTED_VULNERABILITY_DESCRIPTION = """
            File: example/vulnerable_code/XSS_variable_assign.py
             > User input at line 6, trigger word "get(":
                ¤call_1 = ret_request.args.get('param', 'not set')
            Reassigned in: 
                File: example/vulnerable_code/XSS_variable_assign.py
                 > Line 6: param = ¤call_1
                File: example/vulnerable_code/XSS_variable_assign.py
                 > Line 8: other_var = param + ''
                File: example/vulnerable_code/XSS_variable_assign.py
                 > Line 11: ¤call_3 = ret_make_response(¤call_4)
                File: example/vulnerable_code/XSS_variable_assign.py
                 > Line 11: resp = ¤call_3
                File: example/vulnerable_code/XSS_variable_assign.py
                 > Line 12: ret_XSS1 = resp
            File: example/vulnerable_code/XSS_variable_assign.py
             > reaches line 11, trigger word "replace(": 
                ¤call_4 = ret_html.replace('{{ param }}', other_var)
        """

        self.assertTrue(self.string_compare_alpha(vulnerability_description, EXPECTED_VULNERABILITY_DESCRIPTION))

    def test_XSS_variable_multiple_assign_result(self):
        vulnerability_log = self.run_analysis('example/vulnerable_code/XSS_variable_multiple_assign.py')
        self.assert_length(vulnerability_log.vulnerabilities, expected_length=1)
        vulnerability_description = str(vulnerability_log.vulnerabilities[0])
        EXPECTED_VULNERABILITY_DESCRIPTION = """
            File: example/vulnerable_code/XSS_variable_multiple_assign.py
             > User input at line 6, trigger word "get(":
                ¤call_1 = ret_request.args.get('param', 'not set')
            Reassigned in: 
                File: example/vulnerable_code/XSS_variable_multiple_assign.py
                 > Line 6: param = ¤call_1
                File: example/vulnerable_code/XSS_variable_multiple_assign.py
                 > Line 8: other_var = param + ''
                File: example/vulnerable_code/XSS_variable_multiple_assign.py
                 > Line 10: not_the_same_var = '' + other_var
                File: example/vulnerable_code/XSS_variable_multiple_assign.py
                 > Line 12: another_one = not_the_same_var + ''
                File: example/vulnerable_code/XSS_variable_multiple_assign.py
                 > Line 15: ¤call_3 = ret_make_response(¤call_4)
                File: example/vulnerable_code/XSS_variable_multiple_assign.py
                 > Line 15: resp = ¤call_3
                File: example/vulnerable_code/XSS_variable_multiple_assign.py
                 > Line 17: ret_XSS1 = resp
            File: example/vulnerable_code/XSS_variable_multiple_assign.py
             > reaches line 15, trigger word "replace(": 
                ¤call_4 = ret_html.replace('{{ param }}', another_one)
        """

        self.assertTrue(self.string_compare_alpha(vulnerability_description, EXPECTED_VULNERABILITY_DESCRIPTION))
