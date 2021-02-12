/* global PypeHarmony:writable, include */
// ***************************************************************************
// *                        CollectCurrentFile                               *
// ***************************************************************************


// check if PypeHarmony is defined and if not, load it.
if (typeof PypeHarmony !== 'undefined') {
    var PYPE_HARMONY_JS = System.getenv('PYPE_HARMONY_JS');
    include(PYPE_HARMONY_JS + '/pype_harmony.js');
}


/**
 * @namespace
 * @classdesc Collect Current file
 */
var CollectCurrentFile = function() {};

CollectCurrentFile.prototype.collect = function() {
    return (
        scene.currentProjectPath() + '/' +
            scene.currentVersionName() + '.xstage'
    );
};

// add self to Pype Loaders
PypeHarmony.Publish.CollectCurrentFile = new CollectCurrentFile();
