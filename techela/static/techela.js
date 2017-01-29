Jupyter.keyboard_manager.command_shortcuts.add_shortcut('c', {
    help : 'Add comment cell.',
    help_index : 'zz',
    handler : function (event)
    {Jupyter.notebook.insert_cell_below();
     Jupyter.notebook.select_next();
     Jupyter.notebook.to_markdown();
     Jupyter.notebook.edit_mode();

     var kernel = Jupyter.notebook.kernel;
     kernel.execute("import getpass; username=getpass.getuser(); print(username)",		       
		    {iopub: {output: function(response) {                                
			var resp = response.content.text;      
			console.log(response.content);
			var comment = prompt("Comment: ")
			var text = '<font color="red">' + resp + ": "+ comment + '</font>';
			   Jupyter.notebook.get_selected_cell().set_text(text);
			   Jupyter.notebook.execute_cell();}}},
		    {silent: false, 
		     store_history: false, 
		     stop_on_error: true})}});

Jupyter.keyboard_manager.command_shortcuts.add_shortcut('g', {
    help : 'Add grade',
    help_index : 'zz',
    handler : function (event)
    {function letter_to_number(letter)
     {var n = "none";
      if (letter == 'A++')  {n=1.0}
      else if (letter == 'A+')  {n=0.95}
      else if (letter == 'A')  {n=0.9}
      else if (letter == 'A-')  {n=0.85}
      else if (letter == 'A/B')  {n=0.8}
      else if (letter == 'B+')  {n=0.75}
      else if (letter == 'B')  {n=0.7}
      else if (letter == 'B-')  {n=0.65}
      else if (letter == 'B/C')  {n=0.6}
      else if (letter == 'C+')  {n=0.55}
      else if (letter == 'C')  {n=0.5}
      else if (letter == 'C-')  {n=0.45}
      else if (letter == 'C/D')  {n=0.4}
      else if (letter == 'D+')  {n=0.35}
      else if (letter == 'D')  {n=0.3}
      else if (letter == 'D-')  {n=0.25}
      else if (letter == 'D/R')  {n=0.2}
      else if (letter == 'R+')  {n=0.15}
      else if (letter == 'R')  {n=0.1}
      else if (letter == 'R-')  {n=0.05}
      else if (letter == 'R--')  {n=0};
	    return n};
	
     // I don't currently use this. I need to actually store a rubric in the metadata first. Another day perhaps.
     // var rubric = Jupyter.notebook.metadata.org.RUBRIC
     
     var tech = prompt('Technical grade: ').toUpperCase();
     var pres = prompt('Presentation grade: ').toUpperCase();
     var grade = 0.7 * letter_to_number(tech) + 0.3 * letter_to_number(pres);

     var lettergrade;
     if (grade == "none") {lettergrade="unfinished"}
     else if (grade == 1.0) {lettergrade="A++"}
     else if (grade >= 0.95) {lettergrade="A+"}
     else if (grade >= 0.90) {lettergrade="A"}
     else if (grade >= 0.85) {lettergrade="A-"}
     else if (grade >= 0.80) {lettergrade="A/B"}
     else if (grade >= 0.75) {lettergrade="B+"}
     else if (grade >= 0.70) {lettergrade="B"}
     else if (grade >= 0.65) {lettergrade="B-"}
     else if (grade >= 0.60) {lettergrade="B/C"}
     else if (grade >= 0.55) {lettergrade="C+"}
     else if (grade >= 0.50) {lettergrade="C"}
     else if (grade >= 0.45) {lettergrade="C-"}
     else if (grade >= 0.40) {lettergrade="C/R"}
     else if (grade >= 0.35) {lettergrade="D+"}
     else if (grade >= 0.30) {lettergrade="D"}
     else if (grade >= 0.25) {lettergrade="D-"}
     else if (grade >= 0.20) {lettergrade="D/R"}
     else if (grade >= 0.15) {lettergrade="R+"}
     else if (grade >= 0.10) {lettergrade="R"}
     else if (grade >= 0.05) {lettergrade="R-"}
     else {lettergrade = "R--"};
     
     Jupyter.notebook.metadata.grade = {};
     Jupyter.notebook.metadata.grade.technical = tech;
     Jupyter.notebook.metadata.grade.presentation = pres;
     Jupyter.notebook.metadata.grade.overall = grade;

     var kernel = Jupyter.notebook.kernel;
     kernel.execute("import getpass; username=getpass.getuser(); print(username)",		       
		    {iopub: {output: function(response) {                                
			var username = response.content.text;      

			var cells = Jupyter.notebook.get_cells()
			var N = cells.length
			Jupyter.notebook.select(N - 1)
			Jupyter.notebook.insert_cell_below();
			Jupyter.notebook.select_next();
			Jupyter.notebook.edit_mode();
			var text = "Technical: " + String(tech) + "\n\nPresentation: " + String(pres) + "\n\nGrade: " + String(grade) + " (" + lettergrade + ")\n\n" + "Graded by: " + username;
			
			Jupyter.notebook.get_selected_cell().set_text(text);
			Jupyter.notebook.to_markdown();
			Jupyter.notebook.execute_cell();}}},
		    {silent: false, 
		     store_history: false, 
		     stop_on_error: true});
     Jupyter.notebook.save_notebook();
     Jupyter.notebook.save_checkpoint();}});

