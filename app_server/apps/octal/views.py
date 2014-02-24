import json

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse
from lazysignup.decorators import allow_lazy_user

from apps.octal.models import Exercises, Responses, ExerciseAttempts, ExerciseConcepts
from apps.cserver_comm.cserver_communicator import get_full_graph_json_str, get_id_to_concept_dict
from apps.user_management.models import Profile

from apps.octal.knowledgeInference import performInference

#TODO remove me
from django.views.decorators.csrf import csrf_exempt


def get_octal_app(request):
    if request.user.is_authenticated():
        uprof, created = Profile.objects.get_or_create(pk=request.user.pk)
        lset = set()
        sset = set()
        [lset.add(lc.id) for lc in uprof.learned.all()]
        [sset.add(sc.id) for sc in uprof.starred.all()]
        concepts = {"concepts": [{"id": uid, "learned": uid in lset, "starred": uid in sset} for uid in lset.union(sset)]}
    else:
        concepts = {"concepts": []}
    return render_to_response("octal-app.html", 
                              {
                                "full_graph_skeleton": get_full_graph_json_str(),
                                "user_data": json.dumps(concepts)
                              },
                              context_instance=RequestContext(request))

def fetch_attempt_id(user, con, ex):
    try:
        # try to recycle an unused attempt id
        attempt = ExerciseAttempts.objects.get(uprofile=user, 
                                               exercise=ex,
                                               submitted=False)
        #filter(uprofile=user).filter(exercise=ex).get(submitted=False)
    except ExerciseAttempts.DoesNotExist:
        attempt = ExerciseAttempts(uprofile=user, exercise=ex, concept=con)
        attempt.save()
    return attempt.pk;


@allow_lazy_user
def handle_exercise_request(request, conceptId=""):
    #does the requested concept exist?
    concept_dict = get_id_to_concept_dict()
    if conceptId not in concept_dict: 
        return HttpResponse(status=422)

    user, pcreated = Profile.objects.get_or_create(pk=request.user.pk)
    eCon, ccreated = ExerciseConcepts.objects.get_or_create(conceptId=conceptId,
                                name=concept_dict[conceptId]['tag'])

    # fetch a question for the given concept
    try:
        #order_by('?') probably makes this slow
        ex = Exercises.objects.filter(concepts=eCon).order_by('?')[:1].get()
    except Exercises.DoesNotExist:
        return HttpResponse(status=404) 

    # fetch the question answers
    try:
        r = Responses.objects.filter(exercise=ex).order_by("distract")
    except Responses.DoesNotExist:
        return HttpResponse(status=404)

    data = {
        'qid': ex.pk,
        'h': ex.question,
        't': ex.qtype,
        'a': [x.response for x in r],
        'aid': fetch_attempt_id(user, eCon, ex),
    }

    return HttpResponse(json.dumps(data), mimetype='application/json')

@allow_lazy_user
@csrf_exempt #TODO remove me
def handle_exercise_attempt(request, attempt="", correct=""):
    uprof, created = Profile.objects.get_or_create(pk=request.user.pk)
    try:
        # only inject attempts if we have not submitted for this attempt
        ex = ExerciseAttempts.objects.filter(uprofile=uprof).filter(submitted=False).get(pk=attempt)
    except ExerciseAttempts.DoesNotExist, ExerciseAttempts.MultipleObjectsReturned:
        ex = None

    if request.method == "GET":
        return HttpResponse(ex)
    elif request.method == "PUT":
        # only accept data if we were waiting for it
        if ex is None:
            return HttpResponse(status=401)

        correctness = True if int(correct) is 1 else False

        ex.correct = correctness
        ex.submitted = True
        ex.save()

        # provide a new attempt id if it was incorrect
        if correctness:
            return HttpResponse()
        else:
            return HttpResponse(fetch_attempt_id(uprof, ex.concept, ex.exercise))
            
    else:
        return HttpResponse(status=405)

@allow_lazy_user
def handle_knowledge_request(request, conceptID=""):
    if request.method == "GET":
        uprof, created = Profile.objects.get_or_create(pk=request.user.pk)
        ex = ExerciseAttempts.objects.filter(uprofile=uprof).filter(submitted=True)
        r = [e.get_correctness() for e in ex.all()]
        inferences = performInference(r)
        return HttpResponse(json.dumps(inferences), mimetype='application/json')
    else:
        return HttpResponse(status=405)

def build_exercise_db(request):
    concept_dict = get_id_to_concept_dict()
    concepts = {}
    for c in concept_dict:
        tag = concept_dict[c]['tag']
        concepts[tag],t = ExerciseConcepts.objects.get_or_create(conceptId=c, 
                                        name=tag)

    exercises = [
        { 
            'q': "<p>Given the function definition:</p> <p style='text-align:center'><strong><em>f(N) = f(N -1) + f(N - 2)</em></strong></p><p>and an implementation not making use of memoization, what is the most likely asymptotic runtime as a function of N?</p>",
            'c': ["algorithmic_complexity"],
            'a': 'O(2^N)',
            'd': ['O(1)', 'O(N)', 'O(N^2)'],
        },
    ]

    for e in exercises:
        ex,t = Exercises.objects.get_or_create(question=e['q'])
        ex.concepts = [concepts[x] for x in e['c']]
        Responses.objects.get_or_create(exercise=ex, response=e['a'])
        for d in e['d']:
            Responses.objects.get_or_create(exercise=ex, response=d, distract=True)

    return HttpResponse("Done")