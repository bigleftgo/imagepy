import wx, os, sys
import time, threading
sys.path.append('../../../')
import wx.lib.agw.aui as aui
from sciwx.widgets import MenuBar, ToolBar, ChoiceBook, ParaDialog, WorkFlowPanel, ProgressBar
from sciwx.canvas import CanvasNoteBook
from sciwx.grid import GridNoteBook
from sciwx.mesh import Canvas3DNoteBook
from sciwx.text import MDNoteBook, TextNoteBook
from sciwx.plot import PlotFrame
from skimage.data import camera
from sciapp import App, Source
from sciapp.object import Image
from imagepy import root_dir
from .startup import load_plugins, load_tools, load_widgets, load_document, load_dictionary

class ImagePy(wx.Frame, App):
    def __init__( self, parent ):
        wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = 'ImagePy', 
                            size = wx.Size(-1,-1), pos = wx.DefaultPosition, 
                            style = wx.RESIZE_BORDER|wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL )
        App.__init__(self)
        self.auimgr = aui.AuiManager()
        self.auimgr.SetManagedWindow( self )
        self.SetSizeHints( wx.Size(1024,768) )
        
        logopath = os.path.join(root_dir, 'data/logo.ico')
        self.SetIcon(wx.Icon(logopath, wx.BITMAP_TYPE_ICO))

        self.init_menu()
        self.init_tool()
        self.init_canvas()
        self.init_table()
        self.init_mesh()
        self.init_widgets()
        self.init_text()
        self.init_status()
        self._load_all()

        self.Layout()
        self.auimgr.Update()
        self.Fit()
        self.Centre( wx.BOTH )

        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(aui.EVT_AUI_PANE_CLOSE, self.on_pan_close)
        self.source()

    def source(self):
        self.manager('color').add('front', (255, 255, 255))
        self.manager('color').add('back', (0, 0, 0))

    def init_status(self):
        self.stapanel = stapanel = wx.Panel( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
        sizersta = wx.BoxSizer( wx.HORIZONTAL )
        self.txt_info = wx.StaticText( stapanel, wx.ID_ANY, "ImagePy  v0.2", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.txt_info.Wrap( -1 )
        sizersta.Add( self.txt_info, 1, wx.ALIGN_BOTTOM|wx.BOTTOM|wx.LEFT|wx.RIGHT, 2 )
        #self.pro_bar = wx.Gauge( stapanel, wx.ID_ANY, 100, wx.DefaultPosition, wx.Size( 100,15 ), wx.GA_HORIZONTAL )
        self.pro_bar = ProgressBar(stapanel)
        sizersta.Add( self.pro_bar, 0, wx.ALL, 2 )
        stapanel.SetSizer(sizersta)
        class OpenDrop(wx.FileDropTarget):
            def __init__(self, app): 
                wx.FileDropTarget.__init__(self)
                self.app = app
            def OnDropFiles(self, x, y, path):
                self.app.run_macros(["Open>{'path':'%s'}"%i.replace('\\', '/') for i in path])
        stapanel.SetDropTarget(OpenDrop(self))
        self.auimgr.AddPane( stapanel,  aui.AuiPaneInfo() .Bottom() .CaptionVisible( False ).PinButton( True )
            .PaneBorder( False ).Dock().Resizable().FloatingSize( wx.DefaultSize ).DockFixed( True )
            . MinSize(wx.Size(-1, 20)). MaxSize(wx.Size(-1, 20)).Layer( 10 ) )
        
    def _load_all(self):
        lang = Source.manager('config').get('language')
        dic = Source.manager('dictionary').get('common', tag=lang) or {}
        self.auimgr.GetPane(self.widgets).Caption('Widgets')
        self.auimgr.GetPane(self.tablenbwrap).Caption('Table')
        for i in self.auimgr.GetAllPanes():
            i.Caption(dic[i.caption] if i.caption in dic else i.caption)
        self.auimgr.Update()

        plgs, errplg = load_plugins()
        self.load_menu(plgs)
        dtool = Source.manager('tools').get('default')
        tols, errtol = load_tools()
        self.load_tool(tols, dtool or 'Transform')
        wgts, errwgt = load_widgets()
        self.load_widget(wgts)
        err = errplg + errtol + errwgt
        if len(err)>0: 
            err = [('File', 'Name', 'Error')] + err
            cont = '\n'.join(['%-30s\t%-20s\t%s'%i for i in err])
            self.show_txt(cont, 'loading error log')

    def load_all(self): wx.CallAfter(self._load_all)

    def load_menu(self, data):
        self.menubar.clear()
        lang = Source.manager('config').get('language')
        ls = Source.manager('dictionary').gets(tag=lang)
        short = Source.manager('shortcut').gets()
        acc = self.menubar.load(data)
        self.translate(dict([(i,j[i]) for i,j,_ in ls]))(self.menubar)
        self.SetAcceleratorTable(acc)

    def load_tool(self, data, default=None):
        self.toolbar.clear()
        lang = Source.manager('config').get('language')
        ls = Source.manager('dictionary').gets(tag=lang)
        dic = dict([(i,j[i]) for i,j,_ in ls])
        for i, (name, tols) in enumerate(data[1]):
            name = dic[name] if name in dic else name
            self.toolbar.add_tools(name, tols, i==0)
        default = dic[default] if default in dic else default
        if not default is None: self.toolbar.add_pop(os.path.join(root_dir, 'tools/drop.gif'), default)
        self.toolbar.Layout()

    def load_widget(self, data):
        self.widgets.clear()
        lang = Source.manager('config').get('language')
        self.widgets.load(data)
        for cbk in self.widgets.GetChildren():
            for i in range(cbk.GetPageCount()):
                dic = Source.manager('dictionary').get(cbk.GetPageText(i), tag=lang) or {}
                translate = self.translate(dic)
                title = cbk.GetPageText(i)
                cbk.SetPageText(i, dic[title] if title in dic else title)
                self.translate(dic)(cbk.GetPage(i))
        # self.translate(self.widgets)
        
    def init_menu(self):
        self.menubar = MenuBar(self)
        
    def init_tool(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.toolbar = ToolBar(self, True)
        def on_help(evt, tol):
            lang = Source.manager('config').get('language')
            doc = Source.manager('document').get(tol.title, tag=lang)
            self.show_md(doc or 'No Document!', tol.title)
        self.toolbar.on_help = on_help
        self.toolbar.Fit()

        self.auimgr.AddPane(self.toolbar, aui.AuiPaneInfo() .Left()  .PinButton( True )
            .CaptionVisible( True ).Dock().Resizable().FloatingSize( wx.DefaultSize ).MaxSize(wx.Size( 32,-1 ))
            . BottomDockable( True ).TopDockable( False ).Layer( 10 ) )

    def set_background(self, img):
        class ImgArtProvider(aui.AuiDefaultDockArt):
            def __init__(self, img):
                aui.AuiDefaultDockArt.__init__(self)
                self.bitmap = wx.Bitmap(img, wx.BITMAP_TYPE_PNG)

            def DrawBackground(self, dc, window, orient, rect):
                aui.AuiDefaultDockArt.DrawBackground(self, dc, window, orient, rect)
                
                memDC = wx.MemoryDC()
                memDC.SelectObject(self.bitmap)
                w, h = self.bitmap.GetWidth(), self.bitmap.GetHeight()
                dc.Blit((rect[2]-w)//2, (rect[3]-h)//2, w, h, memDC, 0, 0, wx.COPY, True)
        self.canvasnb.GetAuiManager().SetArtProvider(ImgArtProvider(img))

    def init_canvas(self):
        self.canvasnbwrap = wx.Panel(self)
        sizer = wx.BoxSizer( wx.VERTICAL )
        self.canvasnb = CanvasNoteBook(self.canvasnbwrap)
        self.set_background(root_dir+'/data/watermark.png')

        sizer.Add( self.canvasnb, 1, wx.EXPAND |wx.ALL, 0 )
        self.canvasnbwrap.SetSizer( sizer )
        self.canvasnbwrap.Layout()
        self.auimgr.AddPane( self.canvasnbwrap, aui.AuiPaneInfo() .Center() .CaptionVisible( False ).PinButton( True ).Dock()
            .PaneBorder( False ).Resizable().FloatingSize( wx.DefaultSize ). BottomDockable( True ).TopDockable( False )
            .LeftDockable( True ).RightDockable( True ) )
        self.canvasnb.Bind( wx.lib.agw.aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.on_new_img)
        self.canvasnb.Bind( wx.lib.agw.aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.on_close_img)

    def init_table(self):
        self.tablenbwrap = wx.Panel(self)
        sizer = wx.BoxSizer( wx.VERTICAL )
        self.tablenb = GridNoteBook( self.tablenbwrap)
        sizer.Add( self.tablenb, 1, wx.EXPAND |wx.ALL, 0 )
        self.tablenbwrap.SetSizer( sizer )
        self.tablenbwrap.Layout()
        
        self.auimgr.AddPane( self.tablenbwrap, aui.AuiPaneInfo() .Bottom() .CaptionVisible( True ).PinButton( True ).Dock().Hide()
            .MaximizeButton( True ).Resizable().FloatingSize((800, 600)).BestSize(( 120,120 )). Caption('Table') . 
            BottomDockable( True ).TopDockable( False ).LeftDockable( True ).RightDockable( True ) )
        self.tablenb.Bind( wx.lib.agw.aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.on_new_tab)
        self.tablenb.Bind( wx.lib.agw.aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.on_close_tab)

    def init_mesh(self):
        self.meshnbwrap = wx.Panel(self)
        sizer = wx.BoxSizer( wx.VERTICAL )
        self.meshnb = Canvas3DNoteBook( self.meshnbwrap)
        sizer.Add( self.meshnb, 1, wx.EXPAND |wx.ALL, 0 )
        self.meshnbwrap.SetSizer( sizer )
        self.meshnbwrap.Layout()

        self.auimgr.AddPane( self.meshnbwrap, aui.AuiPaneInfo() .Bottom() .CaptionVisible( True ).PinButton( True ).Float().Hide()
            .MaximizeButton( True ).Resizable().FloatingSize((800, 600)).BestSize(( 120,120 )). Caption('Meshes') . 
            BottomDockable( True ).TopDockable( False ).LeftDockable( True ).RightDockable( True ) )
        self.meshnb.Bind( wx.lib.agw.aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.on_new_mesh)
        self.meshnb.Bind( wx.lib.agw.aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.on_close_mesh)

    def add_task(self, task):
        self.task_manager.add(task.title, task)
        tasks = self.task_manager.gets()
        tasks = [(p.title, lambda t=p:p.prgs) for n,p,t in tasks]
        self.pro_bar.SetValue(tasks)

    def remove_task(self, task):
        self.task_manager.remove(obj=task)
        tasks = self.task_manager.gets()
        tasks = [(p.title, lambda t=p:p.prgs) for n,p,t in tasks]
        self.pro_bar.SetValue(tasks)

    def init_widgets(self):
        lang = Source.manager('config').get('language')
        dic = Source.manager('dictionary').get('common', tag=lang)
        self.widgets = ChoiceBook(self)
        self.auimgr.AddPane( self.widgets, aui.AuiPaneInfo() .Right().Caption('Widgets') .PinButton( True )
            .Dock().Resizable().FloatingSize( wx.DefaultSize ).MinSize( wx.Size( 266,-1 ) ).Layer( 10 ) )

    def init_text(self):
        self.mdwarp = wx.Panel(self)
        sizer = wx.BoxSizer( wx.VERTICAL )
        self.mdnb = MDNoteBook( self.mdwarp)
        sizer.Add( self.mdnb, 1, wx.EXPAND |wx.ALL, 0 )
        self.mdwarp.SetSizer( sizer )
        self.mdwarp.Layout()

        self.auimgr.AddPane( self.mdwarp, aui.AuiPaneInfo() .Bottom() .CaptionVisible( True ).PinButton( True ).Float().Hide()
            .MaximizeButton( True ).Resizable().FloatingSize((400, 400)).BestSize(( 120,120 )). Caption('MarkDown') . 
            BottomDockable( True ).TopDockable( False ).LeftDockable( True ).RightDockable( True ) )

        self.txtwarp = wx.Panel(self)
        sizer = wx.BoxSizer( wx.VERTICAL )
        self.txtnb = TextNoteBook( self.txtwarp)
        sizer.Add( self.txtnb, 1, wx.EXPAND |wx.ALL, 0 )
        self.txtwarp.SetSizer( sizer )
        self.txtwarp.Layout()

        self.auimgr.AddPane( self.txtwarp, aui.AuiPaneInfo() .Bottom() .CaptionVisible( True ).PinButton( True ).Float().Hide()
            .MaximizeButton( True ).Resizable().FloatingSize((400, 400)).BestSize(( 120,120 )). Caption('TextPanel') . 
            BottomDockable( True ).TopDockable( False ).LeftDockable( True ).RightDockable( True ) )

    def on_pan_close(self, event):
        if event.GetPane().window in [self.toolbar, self.widgets]:
            event.Veto()
        if hasattr(event.GetPane().window, 'close'):
            event.GetPane().window.close()

    def on_new_img(self, event):
        self.add_img(self.canvasnb.canvas().image)
        self.add_img_win(self.canvasnb.canvas())

    def on_close_img(self, event):
        canvas = event.GetEventObject().GetPage(event.GetSelection())
        self.remove_img_win(canvas)
        self.remove_img(canvas.image)

    def on_new_tab(self, event):
        self.add_tab(self.tablenb.grid().table)
        self.add_tab_win(self.tablenb.grid())

    def on_close_tab(self, event):
        grid = event.GetEventObject().GetPage(event.GetSelection())
        self.remove_tab_win(grid)
        self.remove_tab(grid.table)
        
    def on_new_mesh(self, event):
        self.add_mesh(self.meshnb.canvas().mesh)
        self.add_mesh_win(self.meshnb.canvas())

    def on_close_mesh(self, event):
        canvas3d = event.GetEventObject().GetPage(event.GetSelection())
        self.remove_mesh(canvas3d.mesh)
        self.remove_mesh_win(canvas3d)
        
    def set_info(self, value):
        lang = Source.manager('config').get('language')
        dics = Source.manager('dictionary').gets(tag=lang) 
        dic = dict(j for i in dics for j in i[1].items())
        value = dic[value] if value in dic else value
        wx.CallAfter(self.txt_info.SetLabel, value)

    def set_progress(self, value):
        v = max(min(value, 100), 0)
        self.pro_bar.SetValue(v)
        if value==-1:
            self.pro_bar.Hide()
        elif not self.pro_bar.IsShown():
            self.pro_bar.Show()
            self.stapanel.GetSizer().Layout()
        self.pro_bar.Update()

    def on_close(self, event):
        print('close')
        #ConfigManager.write()
        self.auimgr.UnInit()
        del self.auimgr
        self.Destroy()
        Source.manager('config').write()
        sys.exit()

    def _show_img(self, img, title=None):
        canvas = self.canvasnb.add_canvas()
        self.remove_img(canvas.image)
        self.remove_img_win(canvas)
        if not title is None:
            canvas.set_imgs(img)
            canvas.image.name = title
        else: canvas.set_img(img)
        self.add_img(canvas.image)
        self.add_img_win(canvas)

    def show_img(self, img, title=None):
        wx.CallAfter(self._show_img, img, title)

    def _show_table(self, tab, title):
        grid = self.tablenb.add_grid()
        self.remove_tab(grid.table)
        self.remove_tab_win(grid)
        grid.set_data(tab)
        grid.table.name = title
        info = self.auimgr.GetPane(self.tablenbwrap)
        info.Show(True)
        self.auimgr.Update()
        self.add_tab(grid.table)
        self.add_tab_win(grid)

    def show_table(self, tab, title=None):
        wx.CallAfter(self._show_table, tab, title)

    def show_plot(self, title):
        fig = PlotFrame(self)
        fig.figure.title = title
        return fig

    def _show_md(self, cont, title='ImagePy'):
        page = self.mdnb.add_page()
        page.set_cont(cont)
        page.title = title
        info = self.auimgr.GetPane(self.mdwarp)
        info.Show(True)
        self.auimgr.Update()

    def show_md(self, cont, title='ImagePy'):
        wx.CallAfter(self._show_md, cont, title)
        
    def _show_workflow(self, cont, title='ImagePy'):
        pan = WorkFlowPanel(self)
        pan.SetValue(cont)
        info = aui.AuiPaneInfo(). DestroyOnClose(True). Left(). Caption(title)  .PinButton( True ) \
            .Resizable().FloatingSize( wx.DefaultSize ).Dockable(True).Dock().Top().Layer( 5 ) 
        pan.Bind(None, lambda x:self.run_macros(['%s>None'%x]))
        self.auimgr.AddPane(pan, info)
        self.auimgr.Update()

    def show_workflow(self, cont, title='ImagePy'):
        wx.CallAfter(self._show_workflow, cont, title)

    def _show_txt(self, cont, title='ImagePy'):
        page = self.txtnb.add_page()
        page.set_cont(cont)
        page.title = title
        info = self.auimgr.GetPane(self.txtwarp)
        info.Show(True)
        self.auimgr.Update()

    def show_txt(self, cont, title='ImagePy'):
        wx.CallAfter(self._show_txt, cont, title)

    def _show_mesh(self, mesh=None, title=None):
        if mesh is None:
            canvas = self.meshnb.add_canvas()
            canvas.mesh.name = 'Surface'
        elif hasattr(mesh, 'vts'):
            canvas = self.get_mesh_win()
            if canvas is None:
                canvas = self.meshnb.add_canvas()
                canvas.mesh.name = 'Surface'
            canvas.add_surf(title, mesh)
        else:
            canvas = self.meshnb.add_canvas()
            canvas.set_mesh(mesh)
        self.add_mesh(canvas.mesh)
        self.add_mesh_win(canvas)

        info = self.auimgr.GetPane(self.meshnbwrap)
        info.Show(True)
        self.auimgr.Update()

    def show_mesh(self, mesh=None, title=None):
        wx.CallAfter(self._show_mesh, mesh, title)

    def show_widget(self, panel, title='Widgets'):
        obj = self.manager('widget').get(panel.title)
        if obj is None:
            obj = panel(self, self)
            self.manager('widget').add(panel.title, obj)
            self.auimgr.AddPane(obj, aui.AuiPaneInfo().Caption(title).Left().Layer( 15 ).PinButton( True )
                .Float().Resizable().FloatingSize( wx.DefaultSize ).Dockable(True)) #.DestroyOnClose())
        lang = Source.manager('config').get('language')
        dic = Source.manager('dictionary').get(obj.title, tag=lang)
        info = self.auimgr.GetPane(obj)
        info.Show(True).Caption(dic[obj.title] if obj.title in dic else obj.title)
        self.translate(dic)(obj)

        self.Layout()
        self.auimgr.Update()

    def switch_widget(self, visible=None): 
        info = self.auimgr.GetPane(self.widgets)
        info.Show(not info.IsShown() if visible is None else visible)
        self.auimgr.Update()

    def switch_toolbar(self, visible=None): 
        info = self.auimgr.GetPane(self.toolbar)
        info.Show(not info.IsShown() if visible is None else visible)
        self.auimgr.Update()

    def switch_table(self, visible=None): 
        info = self.auimgr.GetPane(self.tablenbwrap)
        info.Show(not info.IsShown() if visible is None else visible)
        self.auimgr.Update()

    def close_img(self, name=None):
        names = self.get_img_name() if name is None else [name]
        for name in names:
            idx = self.canvasnb.GetPageIndex(self.get_img_win(name))
            self.remove_img(self.get_img_win(name).image)
            self.remove_img_win(self.get_img_win(name))
            self.canvasnb.DeletePage(idx)

    def close_table(self, name=None):
        names = self.get_tab_name() if name is None else [name]
        for name in names:
            idx = self.tablenb.GetPageIndex(self.get_tab_win(name))
            self.remove_tab(self.get_tab_win(name).table)
            self.remove_tab_win(self.get_tab_win(name))
            self.tablenb.DeletePage(idx)

    def record_macros(self, cmd):
        obj = self.manager('widget').get(name='Macros Recorder')
        if obj is None or not obj.IsShown(): return
        wx.CallAfter(obj.write, cmd)

    def run_macros(self, cmd, callafter=None):
        cmds = [i for i in cmd]
        def one(cmds, after): 
            cmd = cmds.pop(0)
            title, para = cmd.split('>')
            plg = Source.manager('plugin').get(name=title)()
            after = lambda cmds=cmds: one(cmds, one)
            if len(cmds)==0: after = callafter
            wx.CallAfter(plg.start, self, eval(para), after)
        one(cmds, None)

    def show(self, tag, cont, title):
        tag = tag or 'img'
        if tag=='img':
            self.show_img([cont], title)
        elif tag=='imgs':
            self.show_img(cont, title)
        elif tag=='tab':
            self.show_table(cont, title)
        elif tag=='mc':
            self.run_macros(cont)
        elif tag=='md':
            self.show_md(cont, title)
        elif tag=='wf':
            self.show_workflow(cont, title)
        else: self.alert('no view for %s!'%tag)

    def info(self, cont): 
        wx.CallAfter(self.txt_info.SetLabel, cont)

    def _alert(self, info, title='ImagePy'):
        lang = Source.manager('config').get('language')
        dics = Source.manager('dictionary').gets(tag=lang) 
        dialog = wx.MessageDialog(self, info, title, wx.OK)
        self.translate([i[1] for i in dics])(dialog)
        dialog.ShowModal() == wx.ID_OK
        dialog.Destroy()

    def alert(self, info, title='ImagePy'):
        wx.CallAfter(self._alert, info, title)

    def yes_no(self, info, title='ImagePy'):
        dialog = wx.MessageDialog(self, info, title, wx.YES_NO | wx.CANCEL)
        rst = dialog.ShowModal()
        dialog.Destroy()
        dic = {wx.ID_YES:'yes', wx.ID_NO:'no', wx.ID_CANCEL:'cancel'}
        return dic[rst]

    def getpath(self, title, filt, io, name=''):
        filt = '|'.join(['%s files (*.%s)|*.%s'%(i.upper(),i,i) for i in filt])
        dic = {'open':wx.FD_OPEN, 'save':wx.FD_SAVE}
        dialog = wx.FileDialog(self, title, '', name, filt, dic[io])
        rst = dialog.ShowModal()
        path = dialog.GetPath() if rst == wx.ID_OK else None
        dialog.Destroy()
        return path

    def show_para(self, title, view, para, on_handle=None, on_ok=None, 
        on_cancel=None, on_help=None, preview=False, modal=True):
        lang = Source.manager('config').get('language')
        dic = Source.manager('dictionary').get(name=title, tag=lang)
        dialog = ParaDialog(self, title)
        dialog.init_view(view, para, preview, modal=modal, 
            app=self, translate=self.translate(dic))
        dialog.Bind('cancel', on_cancel)
        dialog.Bind('parameter', on_handle)
        dialog.Bind('commit', on_ok)
        dialog.Bind('help', on_help)
        return dialog.show()

    def translate(self, dic):
        dic = dic or {}
        if isinstance(dic, list):
            dic = dict(j for i in dic for j in i.items())
        def lang(x): return dic[x] if x in dic else x
        def trans(frame):
            if hasattr(frame, 'GetChildren'):
                for i in frame.GetChildren(): trans(i)
            if isinstance(frame, wx.MenuBar):
                for i in frame.GetMenus(): trans(i[0])
                for i in range(frame.GetMenuCount()):
                    frame.SetMenuLabel(i, lang(frame.GetMenuLabel(i)))
                return 'not set title'
            if isinstance(frame, wx.Menu):
                for i in frame.GetMenuItems(): trans(i)
                return 'not set title'
            if isinstance(frame, wx.MenuItem):
                frame.SetItemLabel(lang(frame.GetItemLabel()))
                trans(frame.GetSubMenu())
            if isinstance(frame, wx.Button):
                frame.SetLabel(lang(frame.GetLabel()))
            if isinstance(frame, wx.CheckBox):
                frame.SetLabel(lang(frame.GetLabel()))
            if isinstance(frame, wx.StaticText):
                frame.SetLabel(lang(frame.GetLabel()))
            if hasattr(frame, 'SetTitle'):
                frame.SetTitle(lang(frame.GetTitle()))
            if isinstance(frame, wx.MessageDialog):
                frame.SetMessage(lang(frame.GetMessage()))
            if isinstance(frame, wx.Notebook):
                for i in range(frame.GetPageCount()):
                    frame.SetPageText(i, lang(frame.GetPageText(i)))
            if hasattr(frame, 'Layout'): frame.Layout()
        return trans

if __name__ == '__main__':
    import numpy as np
    import pandas as pd

    app = wx.App(False)
    frame = ImagePy(None)
    frame.Show()
    frame.show_img([np.zeros((512, 512), dtype=np.uint8)], 'zeros')
    #frame.show_img(None)
    frame.show_table(pd.DataFrame(np.arange(100).reshape((10,10))), 'title')
    '''
    frame.show_md('abcdefg', 'md')
    frame.show_md('ddddddd', 'md')
    frame.show_txt('abcdefg', 'txt')
    frame.show_txt('ddddddd', 'txt')
    '''
    app.MainLoop()