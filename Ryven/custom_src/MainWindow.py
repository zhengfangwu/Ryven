import os,  sys

from PySide2.QtGui import QIcon, QKeySequence
from PySide2.QtWidgets import QMainWindow, QFileDialog, QShortcut, QAction, QActionGroup, QMenu, QMessageBox

# parent UI
import custom_src.Console.MainConsole as MainConsole
from custom_src.ScriptUI import ScriptUI
from custom_src.Session import Session
from custom_src.builtin_nodes.Result_NodeInstance import Result_NodeInstance, Result_NodeInstance_MainWidget
from custom_src.builtin_nodes.Val_NodeInstance import Val_NodeInstance, ValNode_Instance_MainWidget
from ui.ui_main_window import Ui_MainWindow

from custom_src.Node import Node, NodePort
from custom_src.custom_list_widgets.ScriptsListWidget import ScriptsListWidget
from custom_src.builtin_nodes.GetVar_NodeInstance import GetVar_NodeInstance
from custom_src.builtin_nodes.SetVar_NodeInstance import SetVar_NodeInstance
from custom_src.global_tools.Debugger import Debugger
from custom_src.Design import Design


class MainWindow(QMainWindow):

    # new_script_created = Signal(Script)

    def __init__(self, config):
        super(MainWindow, self).__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        if MainConsole.main_console is not None:
            self.ui.scripts_console_splitter.addWidget(MainConsole.main_console)
        self.ui.scripts_console_splitter.setSizes([350, 350])
        self.ui.main_splitter.setSizes([120, 800])
        self.setWindowTitle('Ryven')
        self.setWindowIcon(QIcon('../resources/pics/program_icon2.png'))
        self.load_stylesheet('dark')
        self.ui.scripts_tab_widget.removeTab(0)

        # menu actions
        self.flow_design_actions = []
        self.setup_menu_actions()

        # shortcuts
        save_shortcut = QShortcut(QKeySequence.Save, self)
        save_shortcut.activated.connect(self.on_save_project_triggered)
        import_nodes_shortcut = QShortcut(QKeySequence('Ctrl+i'), self)
        import_nodes_shortcut.activated.connect(self.on_import_nodes_triggered)

        # clear temp folder
        if not os.path.exists('temp'):
            os.mkdir('temp')
        for f in os.listdir('temp'):
            os.remove('temp/'+f)

        # GENERAL ATTRIBUTES
        # self.scripts = []
        # self.custom_nodes = []
        # self.all_nodes = [SetVar_Node(), GetVar_Node(), Val_Node(), Result_Node()]
        self.package_names = []
        self.node_packages = {}  # {Node: str}

        self.script_UIs = []

        self.session = Session()
        self.session.new_script_created.connect(self.script_created)
        self.session.script_renamed.connect(self.script_renamed)
        self.session.script_deleted.connect(self.script_deleted)


        # #   holds NI subCLASSES for imported nodes:
        # self.all_node_instance_classes = {
        #     self.all_nodes[0]: SetVar_NodeInstance,
        #     self.all_nodes[1]: GetVar_NodeInstance,
        #     self.all_nodes[2]: Val_NodeInstance,
        #     self.all_nodes[3]: Result_NodeInstance
        # }  # (key: node obj, val: NI subclass) (used in Flow)

        self.register_builtin_nodes()

        #   custom subclasses for input widgets
        #   {node : {str: PortInstanceWidget-subclass}} (used in PortInstance)

        # self.custom_node_input_widget_classes = {}

        # UI
        self.scripts_list_widget = ScriptsListWidget(self.session)
        self.ui.scripts_groupBox.layout().addWidget(self.scripts_list_widget)

        # self.ui.scripts_scrollArea.setWidget(self.scripts_list_widget)
        # self.ui.add_new_script_pushButton.clicked.connect(self.create_new_script_button_pressed)
        # self.ui.new_script_name_lineEdit.returnPressed.connect(self.create_new_script_LE_return_pressed)


        if config['config'] == 'create plain new project':
            # self.create_new_script(title='hello world')
            self.session.create_script(title='hello world')
        elif config['config'] == 'open project':
            print('importing packages...')
            self.import_packages(config['required packages'])
            print('loading project...')
            # self.parse_project(config['content'])
            self.session.load(config['content'])
            print('finished')

        print('''
CONTROLS
placing: right mouse
selecting: left mouse
panning: middle mouse
saving: ctrl+s
        ''')


        Design.set_flow_theme()
        Design.set_flow_theme()  # temporary
        #   the double call is just a temporary fix for an issue I will address in a future release.
        #   Problem: because the signal emitted when setting a flow theme is directly connected to the according slots
        #   in NodeInstance as well as NodeInstance_TitleLabel, the NodeInstance's slot (which starts an animation which
        #   uses the title label's current and theme dependent color) could get called before the title
        #   label's slot has been called to reinitialize this color. This results in wrong color end points for the
        #   title label when activating animations.
        #   This is pretty nasty since I cannot think of a nice fix for this issue other that not letting the slot
        #   methods be called directly from the emitted signal but instead through a defined procedure like before.


        # maybe this will be necessary due to scheduling issues when loading flows
        # for s in self.scripts:
        #     s.flow.viewport().update()

        self.resize(1500, 800)


    def setup_menu_actions(self):
        # flow designs
        for d in Design.flow_themes:
            design_action = QAction(d.name, self)
            self.ui.menuFlow_Design_Style.addAction(design_action)
            design_action.triggered.connect(self.on_design_action_triggered)
            self.flow_design_actions.append(design_action)

        self.ui.actionImport_Nodes.triggered.connect(self.on_import_nodes_triggered)
        self.ui.actionSave_Project.triggered.connect(self.on_save_project_triggered)
        self.ui.actionEnableDebugging.triggered.connect(self.on_enable_debugging_triggered)
        self.ui.actionDisableDebugging.triggered.connect(self.on_disable_debugging_triggered)
        self.ui.actionSave_Pic_Viewport.triggered.connect(self.on_save_scene_pic_viewport_triggered)
        self.ui.actionSave_Pic_Whole_Scene_scaled.triggered.connect(self.on_save_scene_pic_whole_triggered)

        # performance mode
        self.action_set_performance_mode_fast = QAction('Fast', self)
        self.action_set_performance_mode_fast.setCheckable(True)

        self.action_set_performance_mode_pretty = QAction('Pretty', self)
        self.action_set_performance_mode_pretty.setCheckable(True)

        performance_mode_AG = QActionGroup(self)
        performance_mode_AG.addAction(self.action_set_performance_mode_fast)
        performance_mode_AG.addAction(self.action_set_performance_mode_pretty)
        self.action_set_performance_mode_fast.setChecked(True)
        performance_mode_AG.triggered.connect(self.on_performance_mode_changed)

        performance_menu = QMenu('Performance Mode', self)
        performance_menu.addAction(self.action_set_performance_mode_fast)
        performance_menu.addAction(self.action_set_performance_mode_pretty)

        self.ui.menuView.addMenu(performance_menu)

        # animations
        self.action_set_animation_active = QAction('Enabled', self)
        self.action_set_animation_active.setCheckable(True)

        self.action_set_animations_inactive = QAction('Disabled', self)
        self.action_set_animations_inactive.setCheckable(True)

        animation_enabled_AG = QActionGroup(self)
        animation_enabled_AG.addAction(self.action_set_animation_active)
        animation_enabled_AG.addAction(self.action_set_animations_inactive)
        self.action_set_animation_active.setChecked(True)
        animation_enabled_AG.triggered.connect(self.on_animation_enabling_changed)

        animations_menu = QMenu('Animations', self)
        animations_menu.addAction(self.action_set_animation_active)
        animations_menu.addAction(self.action_set_animations_inactive)

        self.ui.menuView.addMenu(animations_menu)

        gen_code_action = QAction('gen src code', self)
        gen_code_action.triggered.connect(self.on_gen_code_triggered)
        self.ui.menuFile.addAction(gen_code_action)

    def load_stylesheet(self, ss):
        ss_content = ''
        try:
            f = open('../resources/stylesheets/'+ss+'.txt')
            ss_content = f.read()
            f.close()
        finally:
            Design.ryven_stylesheet = ss_content
            self.setStyleSheet(ss_content)

    def register_builtin_nodes(self):

        nodes = self.session.register_nodes(
            [
                Node(
                    title='get var',
                    node_inst_class=GetVar_NodeInstance,
                    description='get the value of a script variable',
                    inputs=[
                        NodePort(type_='data', widget='std line edit', widget_pos='besides')
                    ],
                    outputs=[
                        NodePort(type_='data', label='val')
                    ],
                    style='extended',
                    color='#c69a15'
                ),
                Node(
                    title='set var',
                    node_inst_class=SetVar_NodeInstance,
                    description='sets the value of a script variable',
                    inputs=[
                        NodePort(type_='exec'),
                        NodePort(type_='data', label='var',
                                 widget='std line edit m', widget_pos='besides'),
                        NodePort(type_='data', label='val',
                                 widget='std line edit m', widget_pos='besides')
                    ],
                    outputs=[
                        NodePort(type_='exec'),
                        NodePort(type_='data', label='val')
                    ],
                    style='extended',
                    color='#c69a15'
                ),
                Node(
                    title='result',
                    node_inst_class=Result_NodeInstance,
                    description='displays a value converted to string',
                    inputs=[
                        NodePort(type_='data')
                    ],
                    widget=Result_NodeInstance_MainWidget,
                    widget_pos='between ports',
                    style='extended',
                    color='#c69a15'
                ),
                Node(
                    title='val',
                    node_inst_class=Val_NodeInstance,
                    description='returns the evaluated value that is typed into the input field',
                    outputs=[
                        NodePort(type_='data')
                    ],
                    widget=ValNode_Instance_MainWidget,
                    widget_pos='between ports',
                    style='extended',
                    color='#c69a15'
                ),
            ]
        )

        for n in nodes:
            self.node_packages[n] = None

    def on_performance_mode_changed(self, action):
        if action == self.action_set_performance_mode_fast:
            Design.set_performance_mode('fast')
        else:
            Design.set_performance_mode('pretty')

    def on_animation_enabling_changed(self, action):
        if action == self.action_set_animation_active:
            Design.animations_enabled = True
        else:
            Design.animations_enabled = False

    def on_design_action_triggered(self):
        index = self.flow_design_actions.index(self.sender())
        Design.set_flow_theme(Design.flow_themes[index])

    def on_enable_debugging_triggered(self):
        Debugger.enable()

    def on_disable_debugging_triggered(self):
        Debugger.disable()

    def on_save_scene_pic_viewport_triggered(self):
        """Saves a picture of the currently visible viewport."""
        if len(self.session.scripts) == 0:
            return

        file_path = QFileDialog.getSaveFileName(self, 'select file', '', 'PNG(*.png)')[0]
        img = self.session.scripts[self.ui.scripts_tab_widget.currentIndex()].flow.get_viewport_img()
        img.save(file_path)

    def on_save_scene_pic_whole_triggered(self):
        """Saves a picture of the whole currently visible scene."""
        if len(self.session.scripts) == 0:
            return

        file_path = QFileDialog.getSaveFileName(self, 'select file', '', 'PNG(*.png)')[0]
        img = self.session.scripts[self.ui.scripts_tab_widget.currentIndex()].flow.get_whole_scene_img()
        img.save(file_path)

    def on_gen_code_triggered(self):
        self.get_current_script().generate_code()


    def script_created(self, script):
        script_widget = ScriptUI(script)
        self.script_UIs.append(script_widget)
        self.ui.scripts_tab_widget.addTab(script_widget, script.title)

    def script_renamed(self, script):
        self.ui.scripts_tab_widget.setTabText(
            self.script_UIs.index(self.get_script_UI(script)),
            script.title
        )

    def script_deleted(self, script):
        self.ui.scripts_tab_widget.removeTab(
            self.script_UIs.index(self.get_script_UI(script))
        )

    def get_script_UI(self, script):
        script_UI = None
        for sui in self.script_UIs:
            if sui.script == script:
                script_UI = sui
                break
        return script_UI

    # def create_new_script_button_pressed(self):
    #     self.create_new_script(title=self.ui.new_script_name_lineEdit.text())

    # def create_new_script_LE_return_pressed(self):
    #     self.create_new_script(title=self.ui.new_script_name_lineEdit.text())


    # def check_new_script_title_validity(self, title: str) -> bool:
    #     if len(title) == 0:
    #         return False
    #     for s in self.scripts:
    #         if s.title == title:
    #             return False
    #
    #     return True

    # def create_new_script(self, title: str = None, config: dict = None):
    #     new_script = Script(self, title, config)
    #     # new_script.name_changed.connect(self.rename_script)
    #     self.ui.scripts_tab_widget.addTab(new_script.widget, new_script.title)
    #     self.scripts.append(new_script)
    #     self.new_script_created.emit(new_script)
    #     # self.scripts_list_widget.recreate_ui()

    # def rename_script(self, script: Script, new_title: str):
    #     self.ui.scripts_tab_widget.setTabText(self.scripts.index(script), new_title)
    #     script.title = new_title

    # def delete_script(self, script):
    #     index = self.scripts.index(script)
    #     self.ui.scripts_tab_widget.removeTab(index)
    #     del self.scripts[index]

    def get_current_script(self):
        return self.session.scripts[self.ui.scripts_tab_widget.currentIndex()]


    def on_import_nodes_triggered(self):
        file_path = QFileDialog.getOpenFileName(self, 'select nodes file', '../packages', 'Ryven Packages(*.rpc)',)[0]
        if file_path != '':
            self.import_nodes_package(file_path)

    def import_packages(self, packages_list):
        for p in packages_list:
            self.import_nodes_package(p)

    def import_nodes_package(self, file_path):
        j_str = ''
        try:
            f = open(file_path)
            j_str = f.read()
            f.close()
        except FileExistsError or FileNotFoundError:
            Debugger.write('couldn\'t open file')
            return

        # don't import a package twice if it already has been imported
        filename = os.path.splitext(os.path.basename(file_path))
        if filename in self.package_names:
            return

        # Important: translate the package first (metacore files -> src code files)
        PackageTranslator = self.get_class_from_file(file_path='../Ryven_PackageTranslator',
                                                     file_name='Ryven_PackageTranslator',
                                                     class_name='PackageTranslator')
        package_translator = PackageTranslator(os.path.dirname(os.path.abspath(file_path)))

        if self.parse_nodes(j_str,
                            package_path=os.path.dirname(file_path),
                            package_name=os.path.splitext(os.path.basename(file_path))[0]):

            self.package_names.append(filename)



    def parse_nodes(self, j_str, package_path, package_name) -> bool:
        """Parses the nodes from a node package.
        Here, all the classes get imported and for every node a Node object with specific attribute values gets
        created."""

        import json

        # strict=False is necessary to allow control characters like '\n' for newline when loading the json
        j_obj = json.loads(j_str, strict=False)

        # Debugger.write(j_obj['type'])
        if j_obj['type'] != 'Ryven nodes package' and j_obj['type'] != 'vyScriptFP nodes package':  # old syntax
            return False

        j_nodes_list = j_obj['nodes']

        num_nodes = len(j_nodes_list)
        for ni in range(num_nodes):
            j_node = j_nodes_list[ni]
            suc = self.parse_node(j_node, package_name, package_path)
            if not suc:
                # Debugger.write('error while importing nodes')
                return False

        # Debugger.write(len(self.custom_nodes), 'nodes imported')

        return True


    def parse_node(self, j_node, package_name, package_path) -> bool:
        """Parses a node from a nodes package.
        Returns false if it fails."""

        # new_node = Node()

        # loading the node's specifications which get finally set below after importing the classes
        node_title = j_node['title']
        node_class_name = j_node['class name']
        node_description = j_node['description']
        node_type = j_node['type']
        node_has_main_widget = j_node['has main widget']
        node_main_widget_pos = j_node['widget position'] if node_has_main_widget else None
        node_design_style = j_node['design style']
        node_color = j_node['color']

        # Every node has a custom module name which differs from it's name to prevent import issues when using
        # multiple (different) Nodes with same titles. For further info: see node manager
        node_module_name = j_node['module name']
        module_name_separator = '___'

        # CUSTOM CLASS IMPORTS ----------------------------------------------------------------------------
        node_inst_class = None
        main_widget_class = None
        input_widget_classes = {}
        # creating all the necessary path variables here for all potentially imported classes

        #       IMPORT NODE INSTANCE SUBCLASS
        node_instance_class_file_path = package_path + '/nodes/' + node_module_name + '/'
        node_instance_widgets_file_path = node_instance_class_file_path + '/widgets'
        node_instance_filename = node_module_name  # the NI file's name is just the 'module name'
        node_inst_class = self.get_class_from_file(file_path=node_instance_class_file_path,
                                                           file_name=node_instance_filename,
                                                           class_name=node_class_name + '_NodeInstance')
        if node_inst_class is None:
            return False    # error during import

        #       IMPORT MAIN WIDGET
        if node_has_main_widget:
            main_widget_filename = node_module_name + module_name_separator + 'main_widget'
            main_widget_class = self.get_class_from_file(file_path=node_instance_widgets_file_path,
                                                         file_name=main_widget_filename,
                                                         class_name=node_class_name +
                                                                             '_NodeInstance_MainWidget')
            if main_widget_class is None:
                return False     # error during import

        #       IMPORT CUSTOM INPUT WIDGETS
        #       I need to create the dict for the node's potential custom input widgets already here
        for w_name in j_node['custom input widgets']:
            input_widget_filename = node_module_name + module_name_separator + w_name
            custom_widget_class = self.get_class_from_file(file_path=node_instance_widgets_file_path,
                                                           file_name=input_widget_filename,
                                                           class_name=w_name + '_PortInstanceWidget')
            if custom_widget_class is None:
                return False     # error during import

            input_widget_classes[w_name] = custom_widget_class

        # ---------------------------------------------------------------------------------------------------

        j_n_inputs = j_node['inputs']
        inputs = []
        num_inputs = len(j_n_inputs)
        for ii in range(num_inputs):
            # loading info
            j_input = j_n_inputs[ii]
            i_type = j_input['type']
            i_label = j_input['label']
            i_widget_name = None
            i_widget_pos = None
            if i_type == 'data' and j_input['has widget']:
                i_widget_name = j_input['widget name']
                i_widget_pos = j_input['widget position']

            # creating port
            new_input = NodePort(
                type_=i_type,
                label=i_label,
                widget=i_widget_name,
                widget_pos=i_widget_pos
            )
            # new_input.type_ = i_type
            # new_input.label = i_label
            # if i_has_widget:
            #     new_input.widget_name = i_widget_name
            #     new_input.widget_pos = i_widget_pos
            inputs.append(new_input)

        j_n_outputs = j_node['outputs']
        outputs = []
        num_outputs = len(j_n_outputs)
        for oi in range(num_outputs):
            # loading info
            j_output = j_n_outputs[oi]
            o_type = j_output['type']
            o_label = j_output['label']

            # creating port
            new_output = NodePort(
                type_=o_type,
                label=o_label
            )
            # new_output.type_ = o_type
            # new_output.label = o_label
            outputs.append(new_output)

        n = self.session.register_node(
            Node(
                title=node_title,
                type_=node_type,
                description=node_description,
                node_inst_class=node_inst_class,
                widget=main_widget_class,
                widget_pos=node_main_widget_pos,
                inputs=inputs,
                input_widgets=input_widget_classes,
                outputs=outputs,
                style=node_design_style,
                color=node_color
            )
        )

        self.node_packages[n] = package_name

        # # setting the Node's attributes
        # new_node.title = node_title
        # new_node.description = node_description
        # new_node.type_ = node_type
        # new_node.package = package_name
        # new_node.has_main_widget = node_has_main_widget
        # if node_has_main_widget:
        #     new_node.main_widget_pos = node_main_widget_pos
        # new_node.design_style = node_design_style
        # new_node.color = QColor(node_color)
        # new_node.inputs = inputs
        # new_node.outputs = outputs

        # self.custom_nodes.append(new_node)
        # self.all_nodes.append(new_node)

        return True


    def get_class_from_file(self, file_path, file_name, class_name):
        """Returns a class with a given name from a file for instantiation by importing the module.
        Used for all the dynamically imported classes:
            - NodeInstances
            - A NodeInstance's main widget
            - A NodeInstance's custom input widgets
        """
        # Debugger.debug(file_path)
        # Debugger.debug(file_name)
        # Debugger.debug(class_name)
        sys.path.append(file_path)
        try:
            new_module = __import__(file_name, fromlist=[class_name])
        except ModuleNotFoundError as e:
            QMessageBox.warning(self, 'Missing Python module', str(e))
            return None

        new_class = getattr(new_module, class_name)
        return new_class


    # def parse_project(self, j_obj):
    #     if j_obj['general info']['type'] != 'Ryven project file':
    #         return
    #
    #     for s in j_obj['scripts']:  # fill flows
    #         self.create_new_script(config=s)


    def on_save_project_triggered(self):
        file_name = QFileDialog.getSaveFileName(self, 'select location and give file name',
                                                '../saves', 'Ryven Project(*.rpo)')[0]
        if file_name != '':
            self.save_project(file_name)


    def save_project(self, file_name):
        import json

        file = None
        try:
            if os.path.exists(file_name):
                os.remove(file_name)
            file = open(file_name, 'w')
        except FileNotFoundError:
            Debugger.write('couldn\'t open file')
            return


        general_project_info_dict = {'type': 'Ryven project file'}

        scripts_data_list = self.session.serialize()

        required_packages = set()
        for ni in self.session.all_node_instances():
            if self.node_packages[ni.parent_node] is None:
                continue
            required_packages.add(
                self.node_packages[ni.parent_node]
            )

        whole_project_dict = {'general info': general_project_info_dict,
                              'scripts': scripts_data_list,
                              'required packages': list(required_packages)}

        data = json.dumps(whole_project_dict)
        Debugger.write(data)


        file.write(data)
        file.close()